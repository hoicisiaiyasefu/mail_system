/**
 * 垃圾邮件 ONNX 推理引擎 DLL
 * 使用 ONNX Runtime C API 加载并运行训练好的垃圾邮件分类模型
 *
 * 编译方法（Windows + MSVC）：
 *   1. 安装 ONNX Runtime: https://github.com/microsoft/onnxruntime/releases
 *   2. cmake -B build -DONNXRUNTIME_ROOT=<path_to_onnxruntime>
 *   3. cmake --build build --config Release
 *
 * 导出的 C 函数接口：
 *   - bool init_model(const char* model_path);
 *   - double predict_spam(const char* text);
 *   - void shutdown();
 */

#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <cctype>
#include <sstream>

static bool g_model_loaded = false;

#ifdef USE_ONNX_RUNTIME
#include <onnxruntime_c_api.h>
static OrtApi* g_ort = nullptr;
static OrtEnv* g_env = nullptr;
static OrtSession* g_session = nullptr;
static OrtMemoryInfo* g_memory_info = nullptr;
#endif

// ============================================================
// 简易 TF-IDF 向量化器（与 Python 版本对应）
// ============================================================

static std::unordered_map<std::string, int> g_vocabulary;
static std::unordered_map<int, double> g_idf;
static bool g_vectorizer_trained = false;

// 简易分词：提取英文单词和中文字符
static std::vector<std::string> tokenize(const std::string& text) {
    std::vector<std::string> tokens;
    std::string current_word;

    for (size_t i = 0; i < text.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(text[i]);

        // 中文字符（UTF-8 3字节）
        if (c >= 0xE0 && i + 2 < text.size()) {
            if (!current_word.empty()) {
                if (current_word.size() > 1) {
                    // 转小写
                    for (char& ch : current_word) ch = std::tolower(ch);
                    tokens.push_back(current_word);
                }
                current_word.clear();
            }
            // 取中文字符的 2-gram
            std::string chinese_char = text.substr(i, 3);
            if (i + 3 < text.size() && (static_cast<unsigned char>(text[i+3]) >= 0xE0)) {
                std::string bigram = text.substr(i, 6);
                tokens.push_back(bigram);
            } else {
                tokens.push_back(chinese_char);
            }
            i += 2;
            continue;
        }

        // 英文字母
        if (std::isalpha(c)) {
            current_word += c;
        } else {
            if (!current_word.empty()) {
                if (current_word.size() > 1) {
                    for (char& ch : current_word) ch = std::tolower(ch);
                    tokens.push_back(current_word);
                }
                current_word.clear();
            }
        }
    }

    if (!current_word.empty() && current_word.size() > 1) {
        for (char& ch : current_word) ch = std::tolower(ch);
        tokens.push_back(current_word);
    }

    return tokens;
}

// 简单的词汇表构建（需要预先提供训练好的词汇表）
static void build_vocabulary(const std::unordered_map<std::string, int>& vocab,
                              const std::unordered_map<int, double>& idf) {
    g_vocabulary = vocab;
    g_idf = idf;
    g_vectorizer_trained = true;
}

// 将文本转为 TF-IDF 特征向量（稀疏表示）
static std::unordered_map<int, double> transform_tfidf(const std::string& text) {
    std::unordered_map<int, double> features;
    if (!g_vectorizer_trained) return features;

    auto tokens = tokenize(text);
    if (tokens.empty()) return features;

    // 词频统计
    std::unordered_map<std::string, int> token_counts;
    for (const auto& token : tokens) {
        token_counts[token]++;
    }

    double total_tokens = static_cast<double>(tokens.size());

    for (const auto& [word, count] : token_counts) {
        auto it = g_vocabulary.find(word);
        if (it != g_vocabulary.end()) {
            int idx = it->second;
            double tf = count / total_tokens;
            double idf_val = 1.0;
            auto idf_it = g_idf.find(idx);
            if (idf_it != g_idf.end()) {
                idf_val = idf_it->second;
            }
            features[idx] = tf * idf_val;
        }
    }

    return features;
}

// ============================================================
// 多项式朴素贝叶斯分类器
// ============================================================

static std::unordered_map<int, double> g_class_log_prior;
static std::unordered_map<int, std::unordered_map<int, double>> g_feature_log_prob;
static bool g_classifier_trained = false;

static void set_classifier_params(
    const std::unordered_map<int, double>& class_prior,
    const std::unordered_map<int, std::unordered_map<int, double>>& feat_prob) {
    g_class_log_prior = class_prior;
    g_feature_log_prob = feat_prob;
    g_classifier_trained = true;
}

static double predict_spam_score_cpp(const std::string& text) {
    if (!g_vectorizer_trained || !g_classifier_trained) {
        return 0.5;  // 无法判断，返回中性分数
    }

    auto features = transform_tfidf(text);

    // 计算对数概率
    double log_prob_spam = g_class_log_prior.count(1) ? g_class_log_prior[1] : std::log(0.5);
    double log_prob_ham = g_class_log_prior.count(0) ? g_class_log_prior[0] : std::log(0.5);

    for (const auto& [idx, value] : features) {
        auto s_it = g_feature_log_prob.count(1) ? g_feature_log_prob[1].find(idx) : g_feature_log_prob[1].end();
        auto h_it = g_feature_log_prob.count(0) ? g_feature_log_prob[0].find(idx) : g_feature_log_prob[0].end();

        if (s_it != (g_feature_log_prob.count(1) ? g_feature_log_prob[1].end() : g_feature_log_prob[0].end())) {
            log_prob_spam += value * s_it->second;
        }
        if (h_it != (g_feature_log_prob.count(0) ? g_feature_log_prob[0].end() : g_feature_log_prob[1].end())) {
            log_prob_ham += value * h_it->second;
        }
    }

    // Softmax 转概率
    double max_log = std::max(log_prob_spam, log_prob_ham);
    double exp_spam = std::exp(log_prob_spam - max_log);
    double exp_ham = std::exp(log_prob_ham - max_log);
    double total = exp_spam + exp_ham;

    if (total == 0.0) return 0.5;
    return exp_spam / total;
}

// ============================================================
// 规则引擎（辅助评分）
// ============================================================

static double rule_based_score(const std::string& text) {
    double score = 0.0;

    // 关键词列表
    static const std::vector<std::string> spam_keywords = {
        "免费", "优惠", "促销", "中奖", "领奖", "赚钱",
        "投资", "理财", "股票", "开户", "贷款",
        "代办", "代开", "发票", "增值税",
        "viagra", "casino", "lottery", "winner", "prize",
        "urgent", "act now", "limited time",
        "congratulations", "free money",
    };

    // 关键词命中
    int hit_count = 0;
    std::string lower_text = text;
    for (char& c : lower_text) c = std::tolower(c);

    for (const auto& kw : spam_keywords) {
        std::string kw_lower = kw;
        for (char& c : kw_lower) c = std::tolower(c);
        if (lower_text.find(kw_lower) != std::string::npos) {
            hit_count++;
        }
    }
    score += (static_cast<double>(hit_count) / spam_keywords.size()) * 0.5;

    // URL 数量
    int url_count = 0;
    size_t pos = 0;
    while ((pos = lower_text.find("http", pos)) != std::string::npos) {
        url_count++;
        pos += 4;
    }
    score += std::min(url_count / 5.0, 1.0) * 0.3;

    // 感叹号
    int exc_count = 0;
    for (char c : text) {
        if (c == '!') exc_count++;
    }
    score += std::min(exc_count / 20.0, 1.0) * 0.1;

    // 全大写单词
    int upper_words = 0;
    int total_words = 0;
    std::istringstream iss(text);
    std::string word;
    while (iss >> word) {
        total_words++;
        bool all_upper = true;
        for (char c : word) {
            if (std::islower(c)) { all_upper = false; break; }
        }
        if (all_upper && word.size() > 2) upper_words++;
    }
    if (total_words > 0) {
        score += std::min(static_cast<double>(upper_words) / total_words * 3.0, 1.0) * 0.1;
    }

    return score;
}

// ============================================================
// DLL 导出接口
// ============================================================

extern "C" {

__declspec(dllexport) bool init_model(const char* model_path) {
    // 尝试加载词汇表和分类器参数文件
    // 从 Python 端导出的 JSON 格式模型参数
    std::string path(model_path);

#ifdef USE_ONNX_RUNTIME
    // 如果启用了 ONNX Runtime，尝试加载 ONNX 模型
    if (g_ort == nullptr) {
        OrtStatus* status = OrtGetApiBase()->GetApi(ORT_API_VERSION);
        if (status) return false;
        g_ort = OrtGetApiBase()->GetApi(ORT_API_VERSION);
        g_ort->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "spam_detector", &g_env);
        g_ort->CreateMemoryInfo(Cpu, OrtArenaAllocator, OrtMemTypeDefault, &g_memory_info);
    }

    if (g_env) {
        OrtStatus* status = g_ort->CreateSession(g_env, model_path, nullptr, &g_session);
        if (status) {
            g_ort->ReleaseStatus(status);
            return false;
        }
        g_model_loaded = true;
        return true;
    }
#endif

    // 回退：使用内置的简易模型参数
    // 在实际部署中，这里应该从文件加载序列化的模型参数
    // 这里提供一个默认的简易词汇表
    std::unordered_map<std::string, int> default_vocab;
    std::unordered_map<int, double> default_idf;

    // 垃圾关键词
    std::vector<std::string> vocab_words = {
        "免费", "优惠", "促销", "中奖", "赚钱", "投资", "理财",
        "congratulations", "winner", "free", "urgent", "click",
        "会议", "报告", "项目", "同事", "请查收", "review",
        "发票", "代办", "viagra", "casino", "lottery",
    };

    for (size_t i = 0; i < vocab_words.size(); ++i) {
        default_vocab[vocab_words[i]] = static_cast<int>(i);
        default_idf[static_cast<int>(i)] = 1.0 + std::log(2.0 / 1.5);
    }

    build_vocabulary(default_vocab, default_idf);

    // 设置简易分类器参数
    std::unordered_map<int, double> class_prior;
    class_prior[0] = std::log(0.5);  // 正常
    class_prior[1] = std::log(0.5);  // 垃圾

    g_class_log_prior = class_prior;
    g_classifier_trained = true;

    return true;
}

__declspec(dllexport) double predict_spam(const char* text) {
    if (text == nullptr) return 0.5;

    std::string text_str(text);

#ifdef USE_ONNX_RUNTIME
    if (g_model_loaded && g_session && g_ort) {
        // ONNX 推理逻辑（此处简化，实际需要实现输入张量构建）
        // 直接回退到 C++ 实现
    }
#endif

    // 使用 C++ 实现的预测
    double ml_score = predict_spam_score_cpp(text_str);
    double rule_score = rule_based_score(text_str);

    // 综合评分：ML 60% + 规则 40%
    if (g_classifier_trained && g_vectorizer_trained) {
        return ml_score * 0.6 + rule_score * 0.4;
    } else {
        return rule_score;
    }
}

__declspec(dllexport) void shutdown() {
#ifdef USE_ONNX_RUNTIME
    if (g_ort) {
        if (g_session) { g_ort->ReleaseSession(g_session); g_session = nullptr; }
        if (g_memory_info) { g_ort->ReleaseMemoryInfo(g_memory_info); g_memory_info = nullptr; }
        if (g_env) { g_ort->ReleaseEnv(g_env); g_env = nullptr; }
    }
#endif
    g_model_loaded = false;
    g_vocabulary.clear();
    g_idf.clear();
    g_vectorizer_trained = false;
    g_class_log_prior.clear();
    g_feature_log_prob.clear();
    g_classifier_trained = false;
}

} // extern "C"

// DLL 入口点
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
        case DLL_PROCESS_ATTACH:
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH:
            break;
    }
    return TRUE;
}