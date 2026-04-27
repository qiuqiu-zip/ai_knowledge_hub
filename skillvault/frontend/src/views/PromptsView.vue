<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api/client'

interface PromptItem {
  id: number
  title: string
  content: string
  tags: string[]
  is_favorite: boolean
  source_type?: string
  source_refs?: any[]
  created_at: string
  updated_at: string
}

const prompts = ref<PromptItem[]>([])
const selectedRows = ref<PromptItem[]>([])
const listLoading = ref(false)
const creating = ref(false)
const savingEdit = ref(false)
const deleting = ref(false)
const batchDeleting = ref(false)
const createDialogVisible = ref(false)
const togglingFavorite = reactive<Record<number, boolean>>({})

const filters = reactive({
  keyword: '',
})

const createForm = reactive({
  title: '',
  content: '',
  tagsText: '',
  is_favorite: false,
})

const viewDialogVisible = ref(false)
const editDialogVisible = ref(false)
const activePrompt = ref<PromptItem | null>(null)

const editForm = reactive({
  id: 0,
  title: '',
  content: '',
  tagsText: '',
  is_favorite: false,
})

function parseTags(text: string): string[] {
  return text
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
}

function formatDate(ts: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

function contentPreview(content: string, size = 100) {
  if (!content) return ''
  return content.length > size ? `${content.slice(0, size)}...` : content
}

function resetCreateForm() {
  createForm.title = ''
  createForm.content = ''
  createForm.tagsText = ''
  createForm.is_favorite = false
}

async function loadPrompts() {
  listLoading.value = true
  try {
    const params: Record<string, any> = {}
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    const { data } = await api.get('/api/prompts', { params })
    prompts.value = data
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '加载 Prompt 失败')
  } finally {
    listLoading.value = false
  }
}

async function createPrompt() {
  const title = createForm.title.trim()
  const content = createForm.content.trim()
  if (!title) {
    ElMessage.warning('Title 不能为空')
    return
  }
  if (!content) {
    ElMessage.warning('Content 不能为空')
    return
  }

  creating.value = true
  try {
    await api.post('/api/prompts', {
      title,
      content,
      tags: parseTags(createForm.tagsText),
      is_favorite: createForm.is_favorite,
    })
    createDialogVisible.value = false
    resetCreateForm()
    await loadPrompts()
    ElMessage.success('Prompt 创建成功')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function openView(row: PromptItem) {
  activePrompt.value = row
  viewDialogVisible.value = true
}

function openCreateDialog() {
  createDialogVisible.value = true
}

function openEdit(row: PromptItem) {
  editForm.id = row.id
  editForm.title = row.title
  editForm.content = row.content
  editForm.tagsText = (row.tags || []).join(', ')
  editForm.is_favorite = row.is_favorite
  editDialogVisible.value = true
}

async function saveEdit() {
  const title = editForm.title.trim()
  const content = editForm.content.trim()
  if (!title) {
    ElMessage.warning('Title 不能为空')
    return
  }
  if (!content) {
    ElMessage.warning('Content 不能为空')
    return
  }

  savingEdit.value = true
  try {
    await api.put(`/api/prompts/${editForm.id}`, {
      title,
      content,
      tags: parseTags(editForm.tagsText),
      is_favorite: editForm.is_favorite,
    })
    editDialogVisible.value = false
    await loadPrompts()
    ElMessage.success('保存成功')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    savingEdit.value = false
  }
}

async function copyContent(content: string) {
  const text = content || ''
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      ElMessage.success('已复制到剪贴板')
      return
    }
    throw new Error('Clipboard API unavailable')
  } catch {
    // Fallback for non-secure context (e.g. LAN IP over HTTP) or denied clipboard permission.
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()

    let ok = false
    try {
      ok = document.execCommand('copy')
    } catch (error) {
      console.error(error)
      ok = false
    } finally {
      document.body.removeChild(textarea)
    }

    if (ok) {
      ElMessage.success('已复制到剪贴板')
      return
    }
    ElMessage.error('复制失败，请手动复制')
  }
}

async function deleteOne(row: PromptItem) {
  try {
    await ElMessageBox.confirm(`确认删除 Prompt #${row.id} 吗？`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }

  deleting.value = true
  try {
    await api.delete(`/api/prompts/${row.id}`)
    await loadPrompts()
    ElMessage.success('删除成功')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

function onSelectionChange(rows: PromptItem[]) {
  selectedRows.value = rows
}

const selectedIds = computed(() => selectedRows.value.map((r) => r.id))

async function batchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的 Prompt')
    return
  }

  try {
    await ElMessageBox.confirm(`将删除 ${selectedIds.value.length} 条 Prompt，是否继续？`, '批量删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }

  batchDeleting.value = true
  try {
    await api.post('/api/prompts/batch-delete', { ids: selectedIds.value })
    selectedRows.value = []
    await loadPrompts()
    ElMessage.success('批量删除成功')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

async function toggleFavorite(row: PromptItem) {
  if (togglingFavorite[row.id]) return
  togglingFavorite[row.id] = true
  try {
    const { data } = await api.post(`/api/prompts/${row.id}/toggle-favorite`)
    row.is_favorite = !!data.is_favorite
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '收藏切换失败')
  } finally {
    togglingFavorite[row.id] = false
  }
}

function doSearch() {
  loadPrompts()
}

function resetSearch() {
  filters.keyword = ''
  loadPrompts()
}

onMounted(loadPrompts)
</script>

<template>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
    <div>
      <h2 style="margin: 0">Prompts</h2>
      <p style="margin: 4px 0 0; color: #6b7280">Manage reusable prompts and prompt templates</p>
    </div>
    <el-space>
      <el-button type="primary" @click="openCreateDialog">New Prompt</el-button>
      <el-button :loading="listLoading" @click="loadPrompts">Refresh</el-button>
    </el-space>
  </div>

  <el-card style="margin-bottom: 12px">
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px">
      <el-space>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索 title 或 content"
          style="width: 300px"
          clearable
          @keyup.enter="doSearch"
        />
        <el-button @click="doSearch">Search</el-button>
        <el-button @click="resetSearch">Reset</el-button>
      </el-space>
      <el-space>
        <el-button type="danger" :loading="batchDeleting" @click="batchDelete">Batch Delete</el-button>
        <el-button :loading="listLoading" @click="loadPrompts">Refresh</el-button>
      </el-space>
    </div>
  </el-card>

  <el-card>
    <el-table :data="prompts" v-loading="listLoading" @selection-change="onSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="Title" min-width="180" />
      <el-table-column label="Content Preview" min-width="300">
        <template #default="scope">
          <el-link
            type="primary"
            style="display: inline-block; max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
            @click="openView(scope.row)"
          >
            {{ contentPreview(scope.row.content, 100) }}
          </el-link>
        </template>
      </el-table-column>
      <el-table-column label="Tags" min-width="170">
        <template #default="scope">
          <el-space wrap>
            <el-tag v-for="tag in scope.row.tags || []" :key="tag" size="small" type="info">{{ tag }}</el-tag>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column label="Favorite" width="100">
        <template #default="scope">
          <el-button text :loading="togglingFavorite[scope.row.id]" @click="toggleFavorite(scope.row)">
            {{ scope.row.is_favorite ? '★' : '☆' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="Created At" width="170">
        <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="Actions" width="300">
        <template #default="scope">
          <el-space>
            <el-button size="small" @click="openView(scope.row)">View</el-button>
            <el-button size="small" @click="copyContent(scope.row.content)">Copy</el-button>
            <el-button size="small" type="primary" @click="openEdit(scope.row)">Edit</el-button>
            <el-button size="small" type="danger" :loading="deleting" @click="deleteOne(scope.row)">Delete</el-button>
          </el-space>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="No prompts yet. Click &quot;New Prompt&quot; to create one." />
      </template>
    </el-table>
  </el-card>

  <el-dialog v-model="createDialogVisible" title="New Prompt" width="800px">
    <el-form label-width="80px">
      <el-form-item label="Title">
        <el-input v-model="createForm.title" placeholder="Prompt title" />
      </el-form-item>
      <el-form-item label="Content">
        <el-input v-model="createForm.content" type="textarea" :rows="10" placeholder="Prompt content" />
      </el-form-item>
      <el-form-item label="Tags">
        <el-input v-model="createForm.tagsText" placeholder="java, debug, ai" />
      </el-form-item>
      <el-form-item label="Favorite">
        <el-checkbox v-model="createForm.is_favorite">收藏</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">Cancel</el-button>
      <el-button type="primary" :loading="creating" @click="createPrompt">Create</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="viewDialogVisible" :title="activePrompt?.title || 'Prompt Detail'" width="800px">
    <template v-if="activePrompt">
      <p><strong>标题：</strong>{{ activePrompt.title }}</p>
      <p><strong>Tags：</strong>{{ (activePrompt.tags || []).join(', ') || '-' }}</p>
      <p><strong>Favorite：</strong>{{ activePrompt.is_favorite ? '★ Favorite' : '☆ Not Favorite' }}</p>
      <p><strong>创建时间：</strong>{{ formatDate(activePrompt.created_at) }}</p>
      <p><strong>更新时间：</strong>{{ formatDate(activePrompt.updated_at) }}</p>
      <p><strong>来源：</strong>{{ activePrompt.source_type || '-' }}</p>
      <div
        style="
          background: #f7f7f9;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
          max-height: 60vh;
          overflow-y: auto;
        "
      >
        {{ activePrompt.content }}
      </div>
    </template>
    <template #footer>
      <el-button @click="copyContent(activePrompt?.content || '')">Copy Content</el-button>
      <el-button type="primary" @click="activePrompt && openEdit(activePrompt)">Edit</el-button>
      <el-button @click="viewDialogVisible = false">Close</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editDialogVisible" title="Edit Prompt" width="800px">
    <el-form label-width="80px">
      <el-form-item label="Title">
        <el-input v-model="editForm.title" />
      </el-form-item>
      <el-form-item label="Content">
        <el-input v-model="editForm.content" type="textarea" :rows="10" />
      </el-form-item>
      <el-form-item label="Tags">
        <el-input v-model="editForm.tagsText" placeholder="java, debug, ai" />
      </el-form-item>
      <el-form-item label="Favorite">
        <el-checkbox v-model="editForm.is_favorite">收藏</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">Cancel</el-button>
      <el-button type="primary" :loading="savingEdit" @click="saveEdit">Save</el-button>
    </template>
  </el-dialog>
</template>
