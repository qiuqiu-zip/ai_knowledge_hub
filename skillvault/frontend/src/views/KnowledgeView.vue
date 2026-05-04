<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const list = ref<any[]>([])
const loading = ref(false)
const detailLoading = ref(false)
const sourceDocLoading = ref(false)
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)
const keyword = ref('')
const detailVisible = ref(false)
const sourcePreviewVisible = ref(false)
const activeItem = ref<any | null>(null)
const activeSourceDoc = ref<any | null>(null)
const router = useRouter()

const filteredList = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return list.value
  return list.value.filter((item) => {
    const title = getKnowledgeTitle(item).toLowerCase()
    const summary = cleanKnowledgeSummary(item?.summary, 400).toLowerCase()
    const repo = String(item?.repo || '').toLowerCase()
    const filePath = String(item?.file_path || '').toLowerCase()
    return [title, summary, repo, filePath].some((s) => s.includes(q))
  })
})

function normalizeResponse(data: any) {
  if (Array.isArray(data)) {
    return { items: data, total: data.length }
  }
  if (data && Array.isArray(data.items)) {
    return {
      items: data.items,
      total: Number(data.total ?? data.items.length ?? 0),
    }
  }
  return { items: [], total: 0 }
}

function getErrorMessage(error: any, fallback = '操作失败，请稍后重试') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d?.msg || d?.message || String(d)).join('; ')
  }
  if (detail && typeof detail === 'object') {
    return detail.message || JSON.stringify(detail)
  }
  return error?.response?.data?.message || error?.message || fallback
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/knowledge', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
      },
    })
    const normalized = normalizeResponse(data)
    list.value = normalized.items || []
    total.value = normalized.total || 0
    if (currentPage.value > 1 && list.value.length === 0 && total.value > 0) {
      currentPage.value -= 1
      await load()
    }
  } catch (error: any) {
    console.error('[Knowledge] load failed', error)
    ElMessage.error(getErrorMessage(error, '加载知识列表失败，请稍后重试。'))
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const invalidTitles = new Set(['mock summary', 'summary', 'untitled', '未命名', ''])

function isMeaninglessTitle(title?: string) {
  const v = String(title || '').trim().toLowerCase()
  return invalidTitles.has(v)
}

function cleanKnowledgeSummary(input?: string, max = 220) {
  const text = String(input || '').trim()
  if (!text) return '暂无摘要，可查看来源文档。'

  let cleaned = text
    .replace(/\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/^\s*[=\-~`]{3,}\s*$/gm, ' ')
    .replace(/^\s*\.\.\s+(module|code-block|note|_)[^\n]*$/gim, ' ')
    .replace(/^\s*#+\s*/gm, '')
    .replace(/```[\s\S]*?```/g, ' ')

  const lines = cleaned
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((l) => !/^(npm|pnpm|yarn|pip|curl|docker|mvn|gradle)\b/i.test(l))

  cleaned = lines.join(' ').replace(/\s+/g, ' ').trim()
  if (!cleaned) return '暂无摘要，可查看来源文档。'
  if (cleaned.length <= max) return cleaned
  return `${cleaned.slice(0, max)}...`
}

function firstSentence(text: string, max = 48) {
  const sentence = text.split(/[。！？.!?]/).map((s) => s.trim()).find(Boolean) || text
  return sentence.length > max ? `${sentence.slice(0, max)}...` : sentence
}

function getKnowledgeTitle(item: any) {
  const title = String(item?.title || '').trim()
  if (title && !isMeaninglessTitle(title)) return title

  const cleanedSummary = cleanKnowledgeSummary(item?.summary, 260)
  if (cleanedSummary && cleanedSummary !== '暂无摘要，可查看来源文档。') {
    return firstSentence(cleanedSummary, 50)
  }

  const path = String(item?.file_path || '')
  if (path) {
    const seg = path.split('/').filter(Boolean).pop()
    if (seg) return seg
  }
  return '未命名知识'
}

function normalizeTags(raw: any): string[] {
  const banned = new Set(['mock', 'summary', 'test', 'unknown', ''])
  const arr = Array.isArray(raw) ? raw : String(raw || '').split(',')
  return arr
    .map((x) => String(x || '').trim())
    .filter(Boolean)
    .filter((x) => !banned.has(x.toLowerCase()))
}

function formatTime(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function buildReference(item: any) {
  const tags = normalizeTags(item?.tags)
  return [
    `知识：${getKnowledgeTitle(item)}`,
    `来源项目：${item?.repo || '未识别'}`,
    `来源文件：${item?.file_path || '未识别'}`,
    `标签：${tags.length ? tags.join(', ') : '暂无'}`,
    `摘要：${cleanKnowledgeSummary(item?.summary, 360) || '暂无摘要'}`,
  ].join('\n')
}

async function copyText(text: string, successMessage: string, emptyMessage = '暂无可复制内容') {
  if (!text || !String(text).trim()) {
    ElMessage.warning(emptyMessage)
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(successMessage)
  } catch (error) {
    console.error('[Knowledge] copy failed', error)
    ElMessage.error('复制失败，请手动选择内容复制。')
  }
}

function openDetail(item: any) {
  activeItem.value = item
  detailVisible.value = true
}

async function openSourceDocument(item: any) {
  const docId = item?.source_document_id
  if (!docId) {
    ElMessage.warning('暂无来源文档')
    return
  }
  sourcePreviewVisible.value = true
  sourceDocLoading.value = true
  activeSourceDoc.value = {
    id: docId,
    title: item?.document_title || item?.file_path || `文档 #${docId}`,
    repo: item?.repo,
    file_path: item?.file_path,
    source_url: item?.source_url,
    content: '',
  }
  try {
    const { data } = await api.get(`/api/documents/${docId}`)
    activeSourceDoc.value = data || activeSourceDoc.value
  } catch (error: any) {
    console.error('[Knowledge] load source document failed', error)
    ElMessage.error(getErrorMessage(error, '来源文档加载失败，请稍后重试。'))
  } finally {
    sourceDocLoading.value = false
  }
}

function openDocumentsPage(item: any) {
  const docId = item?.source_document_id
  if (!docId) {
    ElMessage.warning('暂无来源文档')
    return
  }
  router.push({ path: '/documents', query: { document_id: String(docId) } })
}

watch(keyword, () => {
  currentPage.value = 1
})

onMounted(load)
</script>

<template>
  <section>
    <el-card shadow="never" class="knowledge-panel">
      <div class="toolbar-row">
        <el-input v-model="keyword" placeholder="搜索标题、摘要、来源项目或路径" clearable style="width: 320px" />
        <el-button @click="load">刷新</el-button>
      </div>

      <div class="list-shell">
        <el-table :data="filteredList" v-loading="loading" height="100%">
          <el-table-column label="知识标题" min-width="220">
            <template #default="scope">
              <div class="title-cell">
                <strong>{{ getKnowledgeTitle(scope.row) }}</strong>
                <div class="source-hint">
                  {{ scope.row.repo || '来源未识别' }}
                  <span v-if="scope.row.file_path"> · {{ scope.row.file_path }}</span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="摘要" min-width="340">
            <template #default="scope">
              <div class="summary-cell">{{ cleanKnowledgeSummary(scope.row.summary, 220) }}</div>
            </template>
          </el-table-column>

          <el-table-column label="标签" width="220">
            <template #default="scope">
              <div class="tags-cell">
                <template v-if="normalizeTags(scope.row.tags).length">
                  <el-tag v-for="tag in normalizeTags(scope.row.tags)" :key="tag" size="small" type="info">{{ tag }}</el-tag>
                </template>
                <span v-else class="muted">暂无标签</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="260" fixed="right">
            <template #default="scope">
              <el-space>
                <el-button size="small" @click="openDetail(scope.row)">查看详情</el-button>
                <el-button size="small" @click="openSourceDocument(scope.row)" :disabled="!scope.row.source_document_id">查看来源文档</el-button>
                <el-dropdown trigger="click">
                  <el-button size="small">更多</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="copyText(cleanKnowledgeSummary(scope.row.summary, 500), '已复制摘要')">复制摘要</el-dropdown-item>
                      <el-dropdown-item @click="copyText(buildReference(scope.row), '已复制引用信息')">复制引用</el-dropdown-item>
                      <el-dropdown-item @click="copyText(normalizeTags(scope.row.tags).join(', '), '已复制标签', '暂无可复制标签')">复制标签</el-dropdown-item>
                      <el-dropdown-item :disabled="!scope.row.source_url" @click="scope.row.source_url && window.open(scope.row.source_url, '_blank', 'noopener,noreferrer')">打开 GitHub</el-dropdown-item>
                      <el-dropdown-item :disabled="!scope.row.source_document_id" @click="openDocumentsPage(scope.row)">前往文档页</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </el-space>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty description="暂无知识摘要。同步文档并生成摘要后，系统会在这里沉淀结构化知识。" />
          </template>
        </el-table>
      </div>

      <PaginationBar
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="total"
        @update:current-page="load"
        @update:page-size="load"
      />
    </el-card>

    <el-drawer v-model="detailVisible" size="52%" direction="rtl" :with-header="false">
      <div class="detail-body" v-if="activeItem">
        <div class="detail-head">
          <h3>{{ getKnowledgeTitle(activeItem) }}</h3>
          <div class="detail-meta">
            <el-tag size="small">{{ activeItem.repo || '来源未识别' }}</el-tag>
            <el-tag size="small" type="info">{{ activeItem.file_path || '文件未识别' }}</el-tag>
          </div>
          <div class="detail-time">
            <span>创建：{{ formatTime(activeItem.created_at) }}</span>
            <span>更新：{{ formatTime(activeItem.updated_at) }}</span>
          </div>
        </div>

        <el-card shadow="never" class="detail-section">
          <template #header>摘要</template>
          <div class="detail-summary">{{ cleanKnowledgeSummary(activeItem.summary, 1200) }}</div>
        </el-card>

        <el-card shadow="never" class="detail-section">
          <template #header>标签</template>
          <div class="tags-cell">
            <template v-if="normalizeTags(activeItem.tags).length">
              <el-tag v-for="tag in normalizeTags(activeItem.tags)" :key="tag" size="small" type="success">{{ tag }}</el-tag>
            </template>
            <span v-else class="muted">暂无标签</span>
          </div>
        </el-card>

        <el-card shadow="never" class="detail-section">
          <template #header>来源</template>
          <div class="source-grid">
            <div><b>来源项目：</b>{{ activeItem.repo || '未识别' }}</div>
            <div><b>来源文件：</b>{{ activeItem.file_path || '未识别' }}</div>
            <div><b>来源链接：</b>{{ activeItem.source_url || '暂无可用链接' }}</div>
          </div>
          <div class="detail-actions">
            <el-button size="small" @click="openSourceDocument(activeItem)" :disabled="!activeItem.source_document_id">查看来源文档</el-button>
            <el-button size="small" @click="activeItem.source_url && window.open(activeItem.source_url, '_blank', 'noopener,noreferrer')" :disabled="!activeItem.source_url">打开 GitHub</el-button>
            <el-button size="small" @click="copyText(cleanKnowledgeSummary(activeItem.summary, 800), '已复制摘要')">复制摘要</el-button>
            <el-button size="small" @click="copyText(buildReference(activeItem), '已复制引用信息')">复制引用信息</el-button>
            <el-button size="small" @click="detailVisible = false">关闭</el-button>
          </div>
        </el-card>
      </div>
    </el-drawer>

    <el-drawer v-model="sourcePreviewVisible" size="60%" direction="rtl" :with-header="false">
      <div class="source-doc-body" v-loading="sourceDocLoading" v-if="activeSourceDoc">
        <h3>{{ activeSourceDoc.title || activeSourceDoc.file_path || `文档 #${activeSourceDoc.id}` }}</h3>
        <div class="detail-meta">
          <el-tag size="small">{{ activeSourceDoc.repo || '来源未识别' }}</el-tag>
          <el-tag size="small" type="info">{{ activeSourceDoc.file_path || '文件未识别' }}</el-tag>
        </div>
        <div class="detail-actions">
          <el-button size="small" :disabled="!activeSourceDoc.source_url" @click="activeSourceDoc.source_url && window.open(activeSourceDoc.source_url, '_blank', 'noopener,noreferrer')">打开 GitHub</el-button>
          <el-button size="small" @click="copyText(String(activeSourceDoc.content || ''), '已复制文档内容')" :disabled="!String(activeSourceDoc.content || '').trim()">复制内容</el-button>
          <el-button size="small" @click="sourcePreviewVisible = false">关闭</el-button>
        </div>
        <el-card shadow="never" class="detail-section">
          <template #header>文档原文</template>
          <pre v-if="String(activeSourceDoc.content || '').trim()" class="content-pre">{{ activeSourceDoc.content }}</pre>
          <el-empty v-else description="当前接口未返回完整文档内容。" />
        </el-card>
      </div>
    </el-drawer>
  </section>
</template>

<style scoped>
.knowledge-panel { display: flex; flex-direction: column; }
.toolbar-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.list-shell {
  height: calc(100vh - 400px);
  max-height: calc(100vh - 350px);
  min-height: 280px;
  overflow: auto;
}
.title-cell {
  display: grid;
  gap: 4px;
}
.source-hint {
  color: #64748b;
  font-size: 12px;
}
.summary-cell {
  line-height: 1.6;
  color: #334155;
}
.tags-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.muted {
  color: #94a3b8;
}
.detail-body,
.source-doc-body {
  display: grid;
  gap: 12px;
}
.detail-head h3 {
  margin: 0;
}
.detail-meta {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.detail-time {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.detail-section {
  margin-bottom: 4px;
}
.detail-summary {
  line-height: 1.75;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}
.source-grid {
  display: grid;
  gap: 8px;
}
.detail-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.content-pre {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 56vh;
  overflow: auto;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .list-shell {
    height: auto;
    max-height: 65vh;
    min-height: 240px;
  }

  .toolbar-row {
    flex-wrap: wrap;
  }
}
</style>
