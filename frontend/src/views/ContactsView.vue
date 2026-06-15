<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, UserFilled } from '@element-plus/icons-vue'
import api from '@/api'

const contacts = ref([])
const searchKeyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const editingContact = ref(null)

const form = ref({
  name: '',
  email: '',
  phone: '',
  groupName: '',
  notes: '',
})

async function loadContacts() {
  loading.value = true
  try {
    const res = await api.get('/contacts')
    contacts.value = res.data.contacts || []
  } catch (err) {
    ElMessage.error('加载联系人失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadContacts)

const filteredContacts = computed(() => {
  const kw = searchKeyword.value.toLowerCase()
  if (!kw) return contacts.value
  return contacts.value.filter(
    (c) => c.name.toLowerCase().includes(kw) || c.email.toLowerCase().includes(kw),
  )
})

function handleAdd() {
  editingContact.value = null
  form.value = { name: '', email: '', phone: '', groupName: '', notes: '' }
  dialogVisible.value = true
}

function handleEdit(contact) {
  editingContact.value = contact
  form.value = { ...contact }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name || !form.value.email) {
    ElMessage.warning('姓名和邮箱不能为空')
    return
  }
  try {
    if (editingContact.value) {
      await api.put(`/contacts/${editingContact.value.id}`, form.value)
      ElMessage.success('联系人已更新')
    } else {
      await api.post('/contacts', form.value)
      ElMessage.success('联系人已添加')
    }
    dialogVisible.value = false
    loadContacts()
  } catch (err) {
    ElMessage.error('操作失败：' + (err.response?.data?.error || err.message))
  }
}

async function handleDelete(contact) {
  try {
    await ElMessageBox.confirm(`确定要删除联系人「${contact.name}」吗？`, '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }

  try {
    await api.delete(`/contacts/${contact.id}`)
    ElMessage.success('联系人已删除')
    loadContacts()
  } catch (err) {
    ElMessage.error('删除失败')
  }
}
</script>

<template>
  <div style="max-width: 800px; margin: 0 auto">
    <div class="mail-list-card">
      <div class="mail-toolbar">
        <div style="display: flex; gap: 8px">
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon> 添加联系人
          </el-button>
        </div>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索联系人..."
          :prefix-icon="Search"
          style="width: 260px"
          clearable
        />
      </div>

      <el-table :data="filteredContacts" style="width: 100%" stripe v-loading="loading">
        <el-table-column label="姓名" width="140">
          <template #default="{ row }">
            <span style="font-weight: 500">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="220">
          <template #default="{ row }">{{ row.email }}</template>
        </el-table-column>
        <el-table-column label="电话" width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="分组" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.groupName" size="small">{{ row.groupName }}</el-tag>
            <span v-else style="color: #c0c4cc">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button text size="small" type="primary" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button text size="small" type="danger" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑联系人弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingContact ? '编辑联系人' : '添加联系人'"
      width="480px"
    >
      <el-form label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" placeholder="联系人姓名" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" placeholder="email@example.com" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="手机号码（可选）" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="form.groupName" placeholder="如：同事、朋友、家人" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
