<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'
import MarkdownPreview from '../components/MarkdownPreview.vue'

const docs = ref<any[]>([])
const loading = ref(false)
const detailLoading = ref(false)
const previewVisible = ref(false)
const activeDoc = ref<any | null>(null)
const previewMode = ref<'rendered' | 'cleaned' | 'raw'>('raw')
const documentActionLoading = reactive<Record<string, boolean>>({})
const filters = reactive({ repo: '', docType: '', language: '', recommended: '', hasSummary: '' })
const pagination = reactive({ page: 1, pageSize: 5, total: 0 })
const { t } = useI18n()

async function load() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.repo) params.repo = filters.repo
    if (filters.docType) params.doc_type = filters.docType
    if (filters.language) params.language = filters.language
    if (filters.recommended) params.recommended = filters.recommended === 'yes'
    if (filters.hasSummary) params.has_summary = filters.hasSummary === 'yes'
    const { data } = await api.get('/api/documents', { params })
    docs.value = Array.isArray(data) ? (data || []) : (data.items || [])
    pagination.total = Array.isArray(data) ? docs.value.length : Number(data.total || 0)
  } finally {
    loading.value = false
  }
  if (pagination.page > 1 && docs.value.length === 0 && pagination.total > 0) {
    pagination.page -= 1
    await load()
  }
}

function shortSha(sha?: string) {
  return sha ? sha.slice(0, 7) : '-'
}

function languageText(row: any) {
  const lang = row?.metadata?.language
  if (lang === 'zh' || lang === 'zh-CN') return t('languages.zh')
  if (lang === 'en') return t('languages.en')
  return t('languages.unknown')
}

function docTypeText(row: any) {
  const type = row?.metadata?.doc_type || 'other'
  return t(`docTypes.${type}`)
}

function displayTitle(row: any) {
  if (row?.title?.trim()) return row.title.trim()
  const path = row?.file_path || ''
  if (path) {
    const seg = path.split('/').filter(Boolean).pop()
    return seg || path
  }
  return `文档 #${row?.id ?? '-'}`
}

function shortPath(path?: string) {
  if (!path) return '-'
  if (path.length <= 48) return path
  return `...${path.slice(-45)}`
}

function normalizeGithubLinks(row: any) {
  const sourceUrl = String(row?.source_url || '')
  const repo = String(row?.repo || '')
  let repositoryUrl = ''
  let fileUrl = ''

  if (repo && repo.includes('/')) {
    repositoryUrl = `https://github.com/${repo}`
  }

  if (sourceUrl.startsWith('https://github.com/')) {
    const mRepo = sourceUrl.match(/^https?:\/\/github\.com\/([^/]+\/[^/]+)/i)
    if (mRepo) repositoryUrl = `https://github.com/${mRepo[1]}`
    if (sourceUrl.includes('/blob/')) fileUrl = sourceUrl
    else if (!fileUrl && row?.file_path && repositoryUrl) fileUrl = `${repositoryUrl}/blob/main/${row.file_path}`
  } else if (sourceUrl.startsWith('https://raw.githubusercontent.com/')) {
    const mRaw = sourceUrl.match(/^https?:\/\/raw\.githubusercontent\.com\/([^/]+)\/([^/]+)\/([^/]+)\/(.+)$/i)
    if (mRaw) {
      const [, owner, repoName, branch, path] = mRaw
      repositoryUrl = `https://github.com/${owner}/${repoName}`
      fileUrl = `${repositoryUrl}/blob/${branch}/${path}`
    }
  } else if (!repositoryUrl && sourceUrl) {
    repositoryUrl = sourceUrl
  }

  if (!fileUrl && repositoryUrl && row?.file_path) {
    fileUrl = `${repositoryUrl}/blob/main/${row.file_path}`
  }

  return {
    repositoryUrl: repositoryUrl || '',
    fileUrl: fileUrl || '',
    sourceUrl: sourceUrl || '',
  }
}

function cleanDocumentExcerpt(input?: string, max = 160) {
  const text = String(input || '')
  if (!text.trim()) return '暂无摘要，可打开预览查看原文。'

  let cleaned = text
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<img\b[^>]*>/gi, ' ')
    .replace(/\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/^\s*\|.*\|\s*$/gm, ' ')
    .replace(/^\s*[=\-~`]{3,}\s*$/gm, ' ')
    .replace(/^\s*\.\.\s+[^\n]*$/gm, ' ')
    .replace(/^\s*#+\s*/gm, '')
    .replace(/busuanzi|site_pv|site_uv/gi, ' ')

  const lines = cleaned
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((l) => !/^(npm|pnpm|yarn|pip|curl|docker|mvn|gradle)\b/i.test(l))
    .filter((l) => !/(shields\.io|badgen\.net|stargazers|forks|badge)/i.test(l))
    .filter((l) => !/^(redirect|window\.location|meta refresh)/i.test(l))

  cleaned = lines.join(' ').replace(/\s+/g, ' ').trim()
  if (!cleaned) return '暂无摘要，可打开预览查看原文。'
  if (cleaned.length <= max) return cleaned
  return `${cleaned.slice(0, max)}...`
}

function summaryPreview(row: any) {
  const summary = row?.metadata?.summary
  if (summary) return cleanDocumentExcerpt(summary, 180)
  return cleanDocumentExcerpt(row?.content, 180)
}

function detailSummary(row: any) {
  const summary = row?.metadata?.summary
  if (summary) return cleanDocumentExcerpt(summary, 300)
  return '暂无摘要'
}

async function copyText(text: string | undefined, successMessage: string, emptyMessage = '暂无可复制内容') {
  if (!text || !String(text).trim()) {
    ElMessage.warning(emptyMessage)
    return
  }
  try {
    await navigator.clipboard.writeText(String(text))
    ElMessage.success(successMessage)
  } catch {
    ElMessage.error('复制失败，请手动选择内容复制。')
  }
}

function previewLinks(row: any) {
  const { repositoryUrl, fileUrl, sourceUrl } = normalizeGithubLinks(row)
  return {
    repositoryUrl,
    fileUrl,
    sourceUrl,
    bestFileLikeUrl: fileUrl || sourceUrl || '',
    bestLink: fileUrl || repositoryUrl || sourceUrl || '',
  }
}

function buildReferenceText(row: any) {
  const links = previewLinks(row)
  return [
    `项目：${row?.repo || '未识别'}`,
    `文件：${row?.file_path || '未识别'}`,
    `类型：${docTypeText(row) || '未识别'}`,
    `链接：${links.bestLink || '暂无'}`,
  ].join('\n')
}

function contentSnippet(row: any, max = 800) {
  const content = String(row?.content || '').trim()
  if (content) return content.slice(0, max)
  const summary = String(row?.metadata?.summary || '').trim()
  if (summary) return summary.slice(0, max)
  return ''
}

function isMarkdownLike(row: any) {
  const filePath = String(row?.file_path || '').toLowerCase()
  const title = String(row?.title || '').toLowerCase()
  const docType = String(row?.metadata?.doc_type || row?.document_type || '').toLowerCase()
  if (docType === 'readme' || docType === 'docs' || docType === 'markdown') return true
  if (title.includes('readme')) return true
  if (filePath.endsWith('.md') || filePath.endsWith('.markdown') || filePath.endsWith('.mdx') || filePath.endsWith('.rst')) return true
  if (filePath.endsWith('/readme') || filePath === 'readme') return true
  return false
}

function isValidHttpUrl(url?: string) {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

function openExternalUrl(url?: string) {
  if (!url) {
    ElMessage.warning('暂无可用链接')
    return
  }
  if (!isValidHttpUrl(url)) {
    ElMessage.error('来源链接无效，请检查来源配置')
    return
  }
  try {
    window.open(url, '_blank', 'noopener,noreferrer')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.message || '操作失败，请稍后重试')
  }
}

function handleRowMoreCommand(command: string, row: any) {
  const links = normalizeGithubLinks(row)
  switch (command) {
    case 'repo':
      openExternalUrl(links.repositoryUrl)
      break
    case 'github':
      openExternalUrl(links.fileUrl || links.sourceUrl)
      break
    case 'copy-link':
      copyText(links.bestFileLikeUrl || links.bestLink, t('documents.linkCopied'))
      break
    case 'copy-path':
      copyText(row.file_path, '已复制文件路径')
      break
    case 'chunk':
      handleDocumentAction(row, 'chunk')
      break
    case 'embed':
      handleDocumentAction(row, 'embed')
      break
    case 'summarize':
      handleDocumentAction(row, 'summarize')
      break
    case 'skill-draft':
      handleDocumentAction(row, 'skill-draft')
      break
    default:
      break
  }
}

function actionLoadingKey(documentId: number, action: string) {
  return `${documentId}:${action}`
}

async function handleDocumentAction(row: any, action: 'chunk' | 'embed' | 'summarize' | 'skill-draft') {
  const key = actionLoadingKey(row.id, action)
  if (documentActionLoading[key]) return
  documentActionLoading[key] = true
  try {
    const { data } = await api.post(`/api/documents/${row.id}/${action}`)
    ElMessage.success(t('documents.jobCreated', { id: data.job_id }))
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t('documents.createJobFailed'))
  } finally {
    documentActionLoading[key] = false
  }
}

const activeDocLinks = computed(() => previewLinks(activeDoc.value || {}))
const activeDocContent = computed(() => String(activeDoc.value?.content || activeDoc.value?.raw_content || activeDoc.value?.text || '').trim())
const activeDocCleanedContent = computed(() => cleanDocumentExcerpt(activeDocContent.value, 20000))

function isLowValueDoc(row: any) {
  const path = String(row?.file_path || '').toLowerCase()
  if (!path) return false
  if (/_404\.md$|\/404\.md$|\/404\.html$/.test(path)) return true
  if (/_coverpage\.md$|_navbar\.md$|_sidebar\.md$|_footer\.md$/.test(path)) return true
  const summary = String(row?.metadata?.summary || '').toLowerCase()
  if (summary.includes('redirect') || summary.includes('moved to') || summary.includes('已迁移')) return true
  return false
}

async function openPreview(row: any) {
  previewVisible.value = true
  detailLoading.value = true
  activeDoc.value = row
  previewMode.value = isMarkdownLike(row) ? 'rendered' : 'cleaned'
  try {
    const { data } = await api.get(`/api/documents/${row.id}`)
    activeDoc.value = data || row
    previewMode.value = isMarkdownLike(activeDoc.value) ? 'rendered' : 'cleaned'
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '加载文档详情失败，将展示列表数据')
    activeDoc.value = row
    previewMode.value = isMarkdownLike(row) ? 'rendered' : 'cleaned'
  } finally {
    detailLoading.value = false
  }
}

watch(
  () => [filters.docType, filters.language, filters.recommended, filters.hasSummary],
  async () => {
    pagination.page = 1
    await load()
  },
)

onMounted(load)
</script>

<template>
  <section class="documents-page">
    <el-card shadow="never" class="intro-card">
      这里展示系统从 GitHub 仓库同步下来的 README、docs、API 文档、提示词和示例内容。你可以预览原文，也可以打开对应仓库或文件页面。
    </el-card>

    <el-card shadow="never" class="documents-panel">
      <div class="filters-row">
        <el-input v-model="filters.repo" :placeholder="t('documents.filterRepo')" style="width: 220px" clearable @keyup.enter="pagination.page = 1; load()" />
        <el-select v-model="filters.docType" :placeholder="t('documents.filterDocType')" clearable style="width: 140px">
          <el-option label="README" value="readme" />
          <el-option label="指南" value="guide" />
          <el-option label="文档" value="docs" />
          <el-option label="Skill" value="skill" />
          <el-option label="提示词" value="prompt" />
          <el-option label="API" value="api" />
          <el-option label="示例" value="example" />
        </el-select>
        <el-select v-model="filters.language" :placeholder="t('documents.filterLanguage')" clearable style="width: 120px">
          <el-option :label="t('languages.zh')" value="zh" />
          <el-option :label="t('languages.en')" value="en" />
          <el-option :label="t('languages.unknown')" value="unknown" />
        </el-select>
        <el-select v-model="filters.recommended" :placeholder="t('documents.filterRecommended')" clearable style="width: 140px">
          <el-option :label="t('common.yes')" value="yes" />
          <el-option :label="t('common.no')" value="no" />
        </el-select>
        <el-select v-model="filters.hasSummary" :placeholder="t('documents.filterHasSummary')" clearable style="width: 120px">
          <el-option :label="t('documents.hasSummary')" value="yes" />
          <el-option :label="t('documents.noSummary')" value="no" />
        </el-select>
        <el-button @click="pagination.page = 1; load()">{{ t('common.search') }}</el-button>
        <el-button @click="load">{{ t('common.refresh') }}</el-button>
      </div>

      <div class="list-shell">
        <el-table :data="docs" v-loading="loading" height="100%">
          <el-table-column :label="t('documents.title')" min-width="220">
            <template #default="scope">
              <div class="doc-title-cell">
                <strong>{{ displayTitle(scope.row) }}</strong>
                <div class="doc-sub">{{ shortPath(scope.row.file_path) }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column :label="t('documents.repo')" width="180">
            <template #default="scope">
              <el-link
                v-if="normalizeGithubLinks(scope.row).repositoryUrl"
                :href="normalizeGithubLinks(scope.row).repositoryUrl"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ scope.row.repo || '-' }}
              </el-link>
              <span v-else>{{ scope.row.repo || '-' }}</span>
            </template>
          </el-table-column>

          <el-table-column :label="t('documents.docType')" width="110">
            <template #default="scope">{{ docTypeText(scope.row) }}</template>
          </el-table-column>

          <el-table-column :label="t('documents.lang')" width="90">
            <template #default="scope">{{ languageText(scope.row) }}</template>
          </el-table-column>

          <el-table-column :label="t('common.recommended')" width="90">
            <template #default="scope">
              <el-tag v-if="scope.row?.metadata?.is_recommended" type="success">{{ t('common.recommended') }}</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column :label="t('documents.summaryOrExcerpt')" min-width="320">
            <template #default="scope">
              <div>
                <div>{{ summaryPreview(scope.row) }}</div>
                <div v-if="isLowValueDoc(scope.row)" class="low-value-hint">该文件主要是跳转、封面、导航或装饰内容。</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column :label="t('documents.commit')" width="90">
            <template #default="scope">{{ shortSha(scope.row.commit_sha) }}</template>
          </el-table-column>

          <el-table-column :label="t('common.actions')" width="260" fixed="right">
            <template #default="scope">
              <el-space>
                <el-button size="small" @click="openPreview(scope.row)">预览</el-button>
                <el-button size="small" @click="openPreview(scope.row)">预览文件</el-button>
                <el-dropdown trigger="click" @command="(command: string) => handleRowMoreCommand(command, scope.row)">
                  <el-button size="small">更多</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="repo" :disabled="!normalizeGithubLinks(scope.row).repositoryUrl">查看仓库</el-dropdown-item>
                      <el-dropdown-item command="github" :disabled="!(normalizeGithubLinks(scope.row).fileUrl || normalizeGithubLinks(scope.row).sourceUrl)">打开 GitHub</el-dropdown-item>
                      <el-dropdown-item command="copy-link" :disabled="!(normalizeGithubLinks(scope.row).fileUrl || normalizeGithubLinks(scope.row).sourceUrl || normalizeGithubLinks(scope.row).repositoryUrl)">复制链接</el-dropdown-item>
                      <el-dropdown-item command="copy-path" :disabled="!scope.row.file_path">复制路径</el-dropdown-item>
                      <el-dropdown-item command="chunk" :disabled="documentActionLoading[`${scope.row.id}:chunk`]">切分</el-dropdown-item>
                      <el-dropdown-item command="embed" :disabled="documentActionLoading[`${scope.row.id}:embed`]">向量化</el-dropdown-item>
                      <el-dropdown-item command="summarize" :disabled="documentActionLoading[`${scope.row.id}:summarize`]">生成摘要</el-dropdown-item>
                      <el-dropdown-item command="skill-draft" :disabled="documentActionLoading[`${scope.row.id}:skill-draft`]">生成 Skill 草稿</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </el-space>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty :description="t('documents.emptyDesc')" />
          </template>
        </el-table>
      </div>

      <PaginationBar
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[5, 10, 20, 50]"
        @update:current-page="load"
        @update:page-size="load"
      />
    </el-card>

    <el-drawer v-model="previewVisible" size="65%" direction="rtl" :with-header="false">
      <div class="drawer-body" v-loading="detailLoading">
        <template v-if="activeDoc">
          <div class="drawer-head">
            <h3>{{ displayTitle(activeDoc) }}</h3>
            <div class="drawer-meta">
              <el-tag size="small">{{ activeDoc.repo || '-' }}</el-tag>
              <el-tag size="small" type="info">{{ docTypeText(activeDoc) }}</el-tag>
              <el-tag size="small" type="success">{{ languageText(activeDoc) }}</el-tag>
              <el-tag v-if="activeDoc?.metadata?.is_recommended" size="small" type="warning">推荐</el-tag>
              <el-tag v-if="isLowValueDoc(activeDoc)" size="small" type="danger">低价值文件</el-tag>
            </div>
            <div class="drawer-links">
              <el-button
                size="small"
                :disabled="!activeDocLinks.repositoryUrl"
                @click="openExternalUrl(activeDocLinks.repositoryUrl)"
              >查看仓库</el-button>
              <el-button
                size="small"
                :disabled="!(activeDocLinks.fileUrl || activeDocLinks.sourceUrl)"
                @click="openExternalUrl(activeDocLinks.fileUrl || activeDocLinks.sourceUrl)"
              >打开 GitHub</el-button>
              <el-button size="small" @click="copyText(activeDocContent, '已复制完整内容')">复制内容</el-button>
              <el-button
                size="small"
                :disabled="!activeDocLinks.repositoryUrl"
                @click="copyText(activeDocLinks.repositoryUrl, '已复制仓库链接')"
              >复制仓库链接</el-button>
              <el-button
                size="small"
                :disabled="!activeDocLinks.bestFileLikeUrl"
                @click="copyText(activeDocLinks.bestFileLikeUrl, activeDocLinks.fileUrl ? '已复制文件链接' : '已复制来源链接')"
              >{{ activeDocLinks.fileUrl ? '复制文件链接' : '复制来源链接' }}</el-button>
              <el-button
                size="small"
                :disabled="!activeDoc.file_path"
                @click="copyText(activeDoc.file_path, '已复制文件路径')"
              >复制文件路径</el-button>
              <el-button
                size="small"
                @click="copyText(buildReferenceText(activeDoc), '已复制引用信息')"
              >复制引用信息</el-button>
              <el-button
                size="small"
                :disabled="!contentSnippet(activeDoc)"
                @click="copyText(contentSnippet(activeDoc), '已复制内容片段')"
              >复制内容片段</el-button>
              <el-button size="small" @click="previewVisible = false">关闭</el-button>
            </div>
          </div>

          <el-card shadow="never" class="meta-card">
            <div><b>摘要：</b>{{ detailSummary(activeDoc) }}</div>
            <div v-if="isLowValueDoc(activeDoc)" class="low-value-hint"><b>提示：</b>该文件主要是跳转、封面、导航或装饰内容，不建议作为知识素材。</div>
            <div><b>文件路径：</b>{{ activeDoc.file_path || '-' }}</div>
            <div><b>来源链接：</b>{{ activeDoc.source_url || '暂无可用链接' }}</div>
            <div><b>创建时间：</b>{{ activeDoc.created_at ? new Date(activeDoc.created_at).toLocaleString() : '-' }}</div>
            <div><b>更新时间：</b>{{ activeDoc.updated_at ? new Date(activeDoc.updated_at).toLocaleString() : '-' }}</div>
          </el-card>

          <el-card shadow="never" class="content-card">
            <template #header>
              <div class="content-header">
                <span>文件预览</span>
                <el-segmented
                  v-model="previewMode"
                  :options="[
                    { label: '渲染预览', value: 'rendered' },
                    { label: '清洗文本', value: 'cleaned' },
                    { label: '原文', value: 'raw' },
                  ]"
                />
              </div>
            </template>

            <template v-if="activeDocContent">
              <MarkdownPreview v-if="previewMode === 'rendered'" :content="activeDocCleanedContent || activeDocContent" />
              <pre v-else-if="previewMode === 'cleaned'" class="content-pre">{{ activeDocCleanedContent || '当前文档清洗后无可读正文，可切换到原文查看。' }}</pre>
              <pre v-else class="content-pre">{{ activeDocContent }}</pre>
            </template>
            <el-empty v-else description="当前接口未返回完整文档内容，可打开 GitHub 查看原文件。" />
          </el-card>
        </template>
      </div>
    </el-drawer>
  </section>
</template>

<style scoped>
.intro-card { margin-bottom: 12px; color: #475569; line-height: 1.6; }
.documents-panel {
  display: flex;
  flex-direction: column;
}
.filters-row { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px }
.list-shell {
  height: calc(100vh - 390px);
  min-height: 300px;
  max-height: calc(100vh - 340px);
  overflow: auto;
}
.doc-title-cell { display: grid; gap: 4px; }
.doc-sub { color: #6b7280; font-size: 12px; }
.low-value-hint { color: #b45309; font-size: 12px; margin-top: 4px; }
.drawer-body { display: grid; gap: 12px; }
.drawer-head h3 { margin: 0; }
.drawer-meta { margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; }
.drawer-links { margin-top: 8px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.meta-card { display: grid; gap: 8px; }
.content-card { margin-bottom: 24px; }
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.content-pre {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 58vh;
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
    min-height: 240px;
    max-height: 65vh;
  }

  .content-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
