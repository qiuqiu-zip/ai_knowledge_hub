<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import MarkdownPreview from '../components/MarkdownPreview.vue'
import PaginationBar from '../components/PaginationBar.vue'

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
const { t } = useI18n()

const filters = reactive({
  keyword: '',
})
const pagination = reactive({ page: 1, pageSize: 5, total: 0 })

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

function sourceTypeLabel(sourceType?: string) {
  const key = sourceType || 'unknown'
  const mapped = t(`sourceTypes.${key}`)
  return mapped === `sourceTypes.${key}` ? t('sourceTypes.unknown') : mapped
}

async function loadPrompts() {
  listLoading.value = true
  try {
    const params: Record<string, any> = {}
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    params.page = pagination.page
    params.page_size = pagination.pageSize
    const { data } = await api.get('/api/prompts', { params })
    prompts.value = Array.isArray(data) ? data : (data.items || [])
    pagination.total = Array.isArray(data) ? prompts.value.length : Number(data.total || 0)
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '加载提示词失败')
  } finally {
    listLoading.value = false
  }
  if (pagination.page > 1 && prompts.value.length === 0 && pagination.total > 0) {
    pagination.page -= 1
    await loadPrompts()
  }
}

async function createPrompt() {
  const title = createForm.title.trim()
  const content = createForm.content.trim()
  if (!title) {
    ElMessage.warning(`请输入${t('prompts.titleLabel')}`)
    return
  }
  if (!content) {
    ElMessage.warning(`请输入${t('prompts.contentLabel')}`)
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
    ElMessage.success(t('prompts.createPrompt'))
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
    ElMessage.warning(`请输入${t('prompts.titleLabel')}`)
    return
  }
  if (!content) {
    ElMessage.warning(`请输入${t('prompts.contentLabel')}`)
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
    ElMessage.success(t('common.save'))
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
      ElMessage.success(t('documents.linkCopied'))
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
      ElMessage.success(t('documents.linkCopied'))
      return
    }
    ElMessage.error('复制失败，请手动复制')
  }
}

async function deleteOne(row: PromptItem) {
  try {
    await ElMessageBox.confirm(`确认删除提示词 #${row.id} 吗？`, t('prompts.deleteConfirmTitle'), {
      type: 'warning',
    })
  } catch {
    return
  }

  deleting.value = true
  try {
    await api.delete(`/api/prompts/${row.id}`)
    await loadPrompts()
    ElMessage.success(t('common.delete'))
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
    ElMessage.warning('请先选择要删除的提示词')
    return
  }

  try {
    await ElMessageBox.confirm(`确认删除 ${selectedIds.value.length} 条提示词吗？`, t('prompts.deleteConfirmTitle'), {
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
    ElMessage.success(t('prompts.batchDelete'))
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
  pagination.page = 1
  loadPrompts()
}

function resetSearch() {
  filters.keyword = ''
  pagination.page = 1
  loadPrompts()
}

onMounted(loadPrompts)
</script>

<template>
  <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 12px">
    <el-space>
      <el-button type="primary" @click="openCreateDialog">{{ t('prompts.newPrompt') }}</el-button>
      <el-button :loading="listLoading" @click="loadPrompts">{{ t('common.refresh') }}</el-button>
    </el-space>
  </div>

  <el-card style="margin-bottom: 12px">
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px">
      <el-space>
        <el-input
          v-model="filters.keyword"
          :placeholder="t('prompts.searchPlaceholder')"
          style="width: 300px"
          clearable
          @keyup.enter="doSearch"
        />
        <el-button @click="doSearch">{{ t('common.search') }}</el-button>
        <el-button @click="resetSearch">{{ t('common.reset') }}</el-button>
      </el-space>
      <el-space>
        <el-button type="danger" :loading="batchDeleting" @click="batchDelete">{{ t('prompts.batchDelete') }}</el-button>
        <el-button :loading="listLoading" @click="loadPrompts">{{ t('common.refresh') }}</el-button>
      </el-space>
    </div>
  </el-card>

  <el-card class="prompts-panel">
    <div class="list-shell">
      <el-table :data="prompts" v-loading="listLoading" height="100%" @selection-change="onSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" :label="t('prompts.titleLabel')" min-width="180" />
      <el-table-column :label="t('prompts.contentPreview')" min-width="300">
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
      <el-table-column :label="t('prompts.tagsLabel')" min-width="170">
        <template #default="scope">
          <el-space wrap>
            <el-tag v-for="tag in scope.row.tags || []" :key="tag" size="small" type="info">{{ tag }}</el-tag>
          </el-space>
        </template>
      </el-table-column>
      <el-table-column :label="t('prompts.favorite')" width="100">
        <template #default="scope">
          <el-button text :loading="togglingFavorite[scope.row.id]" @click="toggleFavorite(scope.row)">
            {{ scope.row.is_favorite ? '★' : '☆' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="300">
        <template #default="scope">
          <el-space>
            <el-button size="small" @click="openView(scope.row)">{{ t('common.view') }}</el-button>
            <el-button size="small" @click="copyContent(scope.row.content)">{{ t('common.copy') }}</el-button>
            <el-button size="small" type="primary" @click="openEdit(scope.row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" :loading="deleting" @click="deleteOne(scope.row)">{{ t('common.delete') }}</el-button>
          </el-space>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无提示词，请先创建。" />
      </template>
      </el-table>
    </div>
    <PaginationBar
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :page-sizes="[5, 10, 20, 50]"
      :total="pagination.total"
      @update:current-page="loadPrompts"
      @update:page-size="loadPrompts"
    />
  </el-card>

  <el-dialog v-model="createDialogVisible" :title="t('prompts.newPrompt')" width="900px">
    <el-form label-width="80px">
      <el-form-item :label="t('prompts.titleLabel')">
        <el-input v-model="createForm.title" placeholder="请输入标题" />
      </el-form-item>
      <el-form-item :label="t('prompts.contentLabel')">
        <el-input
          v-model="createForm.content"
          type="textarea"
          :autosize="{ minRows: 14, maxRows: 28 }"
          :placeholder="t('prompts.markdownSupported')"
          class="prompt-markdown-textarea"
        />
      </el-form-item>
      <el-form-item :label="t('prompts.tagsLabel')">
        <el-input v-model="createForm.tagsText" placeholder="例如：java, debug, ai" />
      </el-form-item>
      <el-form-item :label="t('prompts.favorite')">
        <el-checkbox v-model="createForm.is_favorite">{{ t('prompts.favorite') }}</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="creating" @click="createPrompt">{{ t('common.create') }}</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="viewDialogVisible" :title="activePrompt?.title || t('prompts.title')" width="1000px">
    <template v-if="activePrompt">
      <div style="display: flex; flex-direction: column; gap: 12px; max-height: 85vh">
        <el-card shadow="never">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="t('prompts.titleLabel')">{{ activePrompt.title }}</el-descriptions-item>
            <el-descriptions-item :label="t('prompts.favorite')">{{ activePrompt.is_favorite ? '★' : '☆' }}</el-descriptions-item>
            <el-descriptions-item :label="t('prompts.tagsLabel')">{{ (activePrompt.tags || []).join(', ') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ sourceTypeLabel(activePrompt.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(activePrompt.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDate(activePrompt.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <div style="overflow-y: auto; max-height: calc(85vh - 190px)">
          <MarkdownPreview :content="activePrompt.content" />
        </div>
      </div>
    </template>
    <template #footer>
      <el-button @click="copyContent(activePrompt?.content || '')">{{ t('prompts.copyPrompt') }}</el-button>
      <el-button type="primary" @click="activePrompt && openEdit(activePrompt)">{{ t('common.edit') }}</el-button>
      <el-button @click="viewDialogVisible = false">{{ t('common.close') }}</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editDialogVisible" :title="t('prompts.editPrompt')" width="900px">
    <el-form label-width="80px">
      <el-form-item :label="t('prompts.titleLabel')">
        <el-input v-model="editForm.title" />
      </el-form-item>
      <el-form-item :label="t('prompts.contentLabel')">
        <el-input
          v-model="editForm.content"
          type="textarea"
          :autosize="{ minRows: 14, maxRows: 28 }"
          :placeholder="t('prompts.markdownSupported')"
          class="prompt-markdown-textarea"
        />
      </el-form-item>
      <el-form-item :label="t('prompts.tagsLabel')">
        <el-input v-model="editForm.tagsText" placeholder="例如：java, debug, ai" />
      </el-form-item>
      <el-form-item :label="t('prompts.favorite')">
        <el-checkbox v-model="editForm.is_favorite">{{ t('prompts.favorite') }}</el-checkbox>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="savingEdit" @click="saveEdit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.prompt-markdown-textarea :deep(.el-textarea__inner) {
  min-height: 420px;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  line-height: 1.65;
}

.prompts-panel {
  display: flex;
  flex-direction: column;
}

.list-shell {
  height: calc(100vh - 430px);
  max-height: calc(100vh - 370px);
  min-height: 260px;
  overflow: auto;
}

@media (max-width: 960px) {
  .list-shell {
    height: auto;
    max-height: 65vh;
    min-height: 220px;
  }
}
</style>
