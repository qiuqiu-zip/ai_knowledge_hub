<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

type RecItem = {
  document_id?: number
  title?: string
  repo?: string
  file_path?: string
  source_url?: string
  repository_url?: string
  file_url?: string
  display_url?: string
  link_label?: string
  updated_at?: string
  summary?: string
  reason?: string
  change_type?: 'created' | 'updated' | 'recommended' | string
}

type ProjectDoc = {
  document_id?: number
  source_document_id?: number
  title?: string
  file_path?: string
  file_url?: string
  link_label?: string
  change_type?: string
  summary?: string
}

type ProjectGroup = {
  repo?: string
  project_name?: string
  owner?: string
  title?: string
  summary?: string
  repository_url?: string
  display_url?: string
  link_label?: string
  change_types?: string[]
  documents_count?: number
  recommended_count?: number
  documents?: ProjectDoc[]
}

const digests = ref<any[]>([])
const activeDigest = ref<any | null>(null)
const loading = ref(false)
const detailVisible = ref(false)
const generateLoading = ref(false)
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)
const todayStatus = ref<any>(null)
const { t } = useI18n()
const router = useRouter()

function formatDate(ts?: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

function asStats(row: any) {
  return row?.stats_json || {}
}

function asRecommended(row: any): RecItem[] {
  return (asStats(row).recommended_documents || []) as RecItem[]
}

function asProjectGroups(row: any): ProjectGroup[] {
  return (asStats(row).project_groups || []) as ProjectGroup[]
}

function asFailedReasons(row: any): string[] {
  return (asStats(row).failed_reasons || []) as string[]
}

function listSummary(row: any) {
  const s = asStats(row)
  const sources = Number(s.sources_synced || 0)
  const pCreated = Number(s.projects_created || 0)
  const pUpdated = Number(s.projects_updated || 0)
  const pRecs = Number(s.projects_recommended || 0)
  const pTotal = Number(s.projects_total || 0)
  const created = Number(s.documents_created || 0)
  const updated = Number(s.documents_updated || 0)
  const failed = Number(s.failed_jobs || 0)
  const recCount = asRecommended(row).length

  if (failed > 0) return `同步 ${sources} 个源，失败 ${failed} 个任务，请关注异常。`
  if (pTotal > 0) {
    if (pCreated + pUpdated === 0) return `同步 ${sources} 个源，发现 ${pTotal} 个项目，暂无新增项目。`
    return `新增 ${pCreated} 个项目，更新 ${pUpdated} 个项目，推荐 ${pRecs} 个项目。`
  }
  if (created + updated === 0) return `同步 ${sources} 个源，暂无新增或更新内容。`
  if (recCount > 0) return `同步 ${sources} 个源，新增 ${created}，更新 ${updated}，推荐 ${recCount} 个内容。`
  return `同步 ${sources} 个源，新增 ${created}，更新 ${updated}。`
}

function digestConclusion(row: any) {
  const s = asStats(row)
  const sources = Number(s.sources_synced || 0)
  const success = Number(s.succeeded_jobs || 0)
  const failed = Number(s.failed_jobs || 0)
  const created = Number(s.documents_created || 0)
  const updated = Number(s.documents_updated || 0)
  const recCount = asRecommended(row).length

  if (failed > 0) {
    return `今日同步 ${sources} 个 GitHub 数据源，成功 ${success} 个任务，失败 ${failed} 个任务。建议先检查失败任务和数据源状态。`
  }
  if (created + updated === 0) {
    return `今日同步 ${sources} 个 GitHub 数据源，${success} 个任务成功。同步窗口内未发现新增或更新内容，因此暂无新的推荐项目。`
  }
  if (recCount > 0) {
    return `今日同步 ${sources} 个 GitHub 数据源，新增 ${created} 项、更新 ${updated} 项，已整理出 ${recCount} 个值得查看的项目/文档。`
  }
  return `今日同步 ${sources} 个 GitHub 数据源，新增 ${created} 项、更新 ${updated} 项。`
}

function normalizeRecTitle(rec: RecItem) {
  return rec.repo || rec.file_path || rec.title || '未命名内容'
}

function normalizeRecIntro(rec: RecItem) {
  const summary = cleanDigestText(rec.summary || '')
  if (summary) return summary
  return '暂无可读摘要，可查看来源文档。'
}

function changeTypeText(changeType?: string) {
  if (changeType === 'created') return '新增'
  if (changeType === 'recommended') return '推荐'
  return '更新'
}

function displayLink(rec: RecItem) {
  return rec.display_url || rec.repository_url || rec.file_url || rec.source_url || ''
}

function hasRepoLink(rec: RecItem) {
  return Boolean(rec.repository_url)
}

function hasFileLink(rec: RecItem) {
  return Boolean(rec.file_url)
}

function mainLinkLabel(rec: RecItem) {
  if (rec.link_label) return rec.link_label
  const file = (rec.file_path || '').toLowerCase()
  if (file.endsWith('readme.md') || file === 'readme') return '查看README'
  if (rec.file_url) return '查看文件'
  if (rec.repository_url) return '查看仓库'
  return '查看来源'
}

function noRecommendationReason(row: any) {
  const s = asStats(row)
  const created = Number(s.documents_created || 0)
  const updated = Number(s.documents_updated || 0)
  const failed = Number(s.failed_jobs || 0)
  if (failed > 0) return '暂无推荐内容：今日存在失败任务，请先检查同步状态。'
  if (created + updated === 0) return '暂无推荐内容：本日未发现新增或更新项目。'
  return '暂无推荐内容：今日没有符合推荐条件的文档。'
}

function projectLink(group: ProjectGroup) {
  return group.display_url || group.repository_url || ''
}

function projectLinkLabel(group: ProjectGroup) {
  if (group.link_label) return group.link_label
  return projectLink(group) ? '查看仓库' : '查看来源'
}

function projectDocs(group: ProjectGroup): ProjectDoc[] {
  return (group.documents || []) as ProjectDoc[]
}

function projectTags(group: ProjectGroup): string[] {
  return (group.change_types || []).filter(Boolean)
}

function projectTagText(x: string) {
  if (x === 'created') return '新增'
  if (x === 'recommended') return '推荐'
  return '更新'
}

function groupedProjects(row: any): ProjectGroup[] {
  const groups = asProjectGroups(row)
  if (groups.length) return groups
  // fallback for old digest: map recommended_documents to pseudo groups by repo/source
  const map = new Map<string, ProjectGroup>()
  for (const rec of asRecommended(row)) {
    const key = (rec.repo || rec.repository_url || rec.source_url || rec.title || 'unknown').toLowerCase()
    if (!map.has(key)) {
      map.set(key, {
        repo: rec.repo,
        title: rec.repo || rec.title || '未命名项目',
        summary: rec.summary || '该项目暂无可用简介，可点击链接查看详情。',
        repository_url: rec.repository_url,
        display_url: rec.display_url || rec.repository_url || rec.source_url,
        link_label: rec.link_label || '查看来源',
        change_types: [],
        documents_count: 0,
        recommended_count: 0,
        documents: [],
      })
    }
    const g = map.get(key)!
    const ct = rec.change_type || 'updated'
    if (!g.change_types!.includes(ct)) g.change_types!.push(ct)
    g.documents_count = Number(g.documents_count || 0) + 1
    g.recommended_count = Number(g.recommended_count || 0) + 1
    g.documents!.push({
      title: rec.title,
      file_path: rec.file_path,
      file_url: rec.file_url || rec.display_url || rec.source_url,
      link_label: rec.link_label || '查看来源',
      change_type: ct,
      summary: rec.summary,
    })
  }
  return Array.from(map.values())
}

function cleanDigestText(input: string) {
  if (!input) return ''
  let s = String(input)
  s = s.replace(/<!--[\s\S]*?-->/g, ' ')
  s = s.replace(/<script[\s\S]*?<\/script>/gi, ' ')
  s = s.replace(/<style[\s\S]*?<\/style>/gi, ' ')
  s = s.replace(/<img[\s\S]*?>/gi, ' ')
  s = s.replace(/<picture[\s\S]*?<\/picture>/gi, ' ')
  s = s.replace(/!\[[^\]]*]\([^)]*\)/g, ' ')
  s = s.replace(/\[!\[[^\]]*]\([^)]*\)]\([^)]*\)/g, ' ')
  s = s.replace(/<\/?[^>]+>/g, ' ')
  s = s
    .replace(/&nbsp;|&ensp;|&emsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
  s = s.replace(/https?:\/\/raw\.githubusercontent\.com\/\S+\.(png|jpg|jpeg|gif|svg|webp)/gi, ' ')
  s = s.replace(/https?:\/\/\S*(shields\.io|badgen\.net)\S*/gi, ' ')
  s = s.replace(/\b(busuanzi|site[_\s-]?pv|site[_\s-]?uv|site\s+view)\b/gi, ' ')
  s = s.replace(/keep these links\.?\s*translations will automatically update\.?/gi, ' ')
  s = s.replace(/^\s*[=~\-`]{3,}\s*$/gm, ' ')
  s = s.replace(/^\s*\.\.\s+[_\w-]+::?.*$/gm, ' ')
  s = s.replace(/\s+/g, ' ').trim()
  return s
}

function buildCopyText(row: any) {
  const s = asStats(row)
  const recs = asRecommended(row)
  const groups = groupedProjects(row)
  const failedReasons = asFailedReasons(row)
  const date = row?.digest_date || '-'
  const lines: string[] = []

  lines.push(`每日简报 - ${date}`)
  lines.push('')
  lines.push('今日结论')
  lines.push(digestConclusion(row))
  lines.push('')
  lines.push('今日项目')
  if (groups.length) {
    groups.forEach((g, idx) => {
      lines.push(`${idx + 1}. ${g.title || g.repo || '未命名项目'}`)
      lines.push(`   简介：${cleanDigestText(g.summary || '') || '该项目暂无可用简介，可点击链接查看详情。'}`)
      lines.push(`   链接：${projectLink(g) || '-'}`)
      const docNames = projectDocs(g)
        .slice(0, 3)
        .map((d) => d.file_path || d.title || '未命名文档')
      if (docNames.length) lines.push(`   涉及文档：${docNames.join('、')}`)
    })
  } else if (recs.length) {
    recs.forEach((rec, idx) => {
      lines.push(`${idx + 1}. ${normalizeRecTitle(rec)}（${changeTypeText(rec.change_type)}）`)
      lines.push(`   简介：${normalizeRecIntro(rec)}`)
      lines.push(`   链接：${displayLink(rec) || '-'}`)
    })
  } else {
    lines.push(`- ${noRecommendationReason(row)}`)
  }

  lines.push('')
  lines.push('同步概览')
  lines.push(`- 同步来源：${Number(s.sources_synced || 0)} 个`)
  lines.push(`- 成功任务：${Number(s.succeeded_jobs || 0)} 个`)
  lines.push(`- 失败任务：${Number(s.failed_jobs || 0)} 个`)
  lines.push(`- 新增文档：${Number(s.documents_created || 0)} 篇`)
  lines.push(`- 更新文档：${Number(s.documents_updated || 0)} 篇`)
  lines.push(`- 推荐数量：${Number(s.projects_recommended || groups.filter((g) => Number(g.recommended_count || 0) > 0).length || recs.length)} 项`)

  lines.push('')
  lines.push('系统统计')
  lines.push(`- 新增内容分块：${Number(s.chunks_created || 0)}`)
  lines.push(`- 完成向量化：${Number(s.embedded_chunks || 0)}`)
  lines.push(`- 新增摘要：${Number(s.summaries_created || 0)}`)
  lines.push(`- 新生成 Skill 草稿：${Number(s.skill_candidates_created || 0)}`)

  if (failedReasons.length) {
    lines.push('')
    lines.push('失败原因')
    failedReasons.slice(0, 10).forEach((x, i) => lines.push(`${i + 1}. ${x}`))
  }

  return lines.join('\n')
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/digests', { params: { page: currentPage.value, page_size: pageSize.value } })
    digests.value = Array.isArray(data) ? (data || []) : (data.items || [])
    total.value = Array.isArray(data) ? digests.value.length : Number(data.total || 0)
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || t('digest.loadFailed'))
  } finally {
    loading.value = false
  }
  if (currentPage.value > 1 && digests.value.length === 0 && total.value > 0) {
    currentPage.value -= 1
    await load()
  }
  await loadTodayStatus()
}

async function loadTodayStatus() {
  try {
    const { data } = await api.get('/api/digests/today')
    todayStatus.value = data
  } catch {
    todayStatus.value = null
  }
}

async function generateTodayDigest() {
  generateLoading.value = true
  try {
    const { data } = await api.post('/api/digests/generate', {})
    if (data?.created) {
      ElMessage.success(data?.message || `已创建简报任务：job_id=${data.job_id}`)
    } else {
      ElMessage.info(data?.reason || '今日简报任务已存在')
    }
    await load()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '生成简报任务失败')
  } finally {
    generateLoading.value = false
  }
}

function openDetail(row: any) {
  activeDigest.value = row
  detailVisible.value = true
}

function openSourceDocument(doc: any) {
  const docId = doc?.source_document_id || doc?.document_id
  if (!docId) {
    ElMessage.warning('暂无来源文档')
    return
  }
  router.push({ path: '/documents', query: { document_id: String(docId) } })
}

async function copyDigest() {
  if (!activeDigest.value) return
  try {
    await navigator.clipboard.writeText(buildCopyText(activeDigest.value))
    ElMessage.success(t('digest.copied'))
  } catch (error) {
    console.error(error)
    ElMessage.error(t('documents.copyFailed'))
  }
}

async function copySummaryText(text: string) {
  const cleaned = cleanDigestText(text || '')
  if (!cleaned) {
    ElMessage.warning('暂无可复制摘要')
    return
  }
  try {
    await navigator.clipboard.writeText(cleaned)
    ElMessage.success('已复制摘要')
  } catch (error) {
    console.error(error)
    ElMessage.error('复制失败，请手动选择内容复制。')
  }
}

const activeStats = computed(() => asStats(activeDigest.value))
const activeRecommended = computed(() => asRecommended(activeDigest.value))
const activeProjects = computed(() => groupedProjects(activeDigest.value))
const activeRecommendedProjects = computed(() =>
  activeProjects.value.filter((x) => Number(x.recommended_count || 0) > 0)
)
const activeFailedReasons = computed(() => asFailedReasons(activeDigest.value))

onMounted(load)
</script>

<template>
  <section class="digest-page">
    <div class="digest-toolbar">
      <div class="digest-toolbar-actions">
        <el-button :loading="generateLoading" type="primary" plain @click="generateTodayDigest">生成/刷新今日简报</el-button>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>
    <el-alert
      v-if="todayStatus && !todayStatus.exists"
      type="info"
      :closable="false"
      show-icon
      :title="`今日（${todayStatus.digest_date || '-'}）简报尚未生成`"
      description="系统会在定时任务时段自动生成；如果刚完成同步，可点击“生成/刷新今日简报”。"
    />

    <el-card class="digest-table-card" shadow="never">
      <div class="list-shell">
        <el-table :data="digests" v-loading="loading" class="digest-table" height="100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="digest_date" label="日期" width="130" />
        <el-table-column label="摘要" min-width="360">
          <template #default="scope">{{ listSummary(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button size="small" type="primary" @click="openDetail(scope.row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无每日简报">
            <p class="digest-empty-tip">
              可能原因：定时任务尚未运行、今日未到生成时间、worker 未消费任务、当前没有符合条件的数据，或 GitHub 源今日没有新增/更新。
            </p>
          </el-empty>
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
  </section>

  <el-dialog v-model="detailVisible" :title="`每日简报 - ${activeDigest?.digest_date || ''}`" width="1000px" top="4vh">
    <div class="digest-detail-body">
      <section class="detail-section">
        <h3>今日重点推荐</h3>
        <div v-if="activeRecommendedProjects.length" class="rec-list compact">
          <article v-for="group in activeRecommendedProjects.slice(0, 5)" :key="`rec-${group.repo}-${group.title}`" class="rec-item">
            <div class="rec-head">
              <strong>{{ group.title || group.repo || '未命名项目' }}</strong>
            </div>
            <p class="rec-intro">{{ cleanDigestText(group.summary || '') || '暂无可读摘要，可查看来源文档。' }}</p>
            <div class="rec-meta">
              <div class="reason-line">
                <el-tag size="small" type="success">重点推荐</el-tag>
              </div>
              <div class="rec-links">
                <template v-if="projectLink(group)">
                  <a :href="projectLink(group)" target="_blank" rel="noopener noreferrer">{{ projectLinkLabel(group) }}</a>
                </template>
                <template v-else>
                  <span>暂无可用链接</span>
                </template>
                <el-button
                  v-if="projectDocs(group).length && (projectDocs(group)[0].source_document_id || projectDocs(group)[0].document_id)"
                  size="small"
                  text
                  type="primary"
                  @click="openSourceDocument(projectDocs(group)[0])"
                >查看来源文档</el-button>
                <el-button size="small" text @click="copySummaryText(group.summary || '')">复制摘要</el-button>
              </div>
            </div>
          </article>
        </div>
        <p v-else class="muted">
          {{
            Number(activeStats.documents_created || 0) + Number(activeStats.documents_updated || 0) === 0
              ? '暂无推荐项目：本日没有新增或更新项目。'
              : '暂无推荐项目：同步成功，但没有符合推荐条件的内容。'
          }}
        </p>
      </section>

      <section class="detail-section">
        <h3>今日结论</h3>
        <p class="conclusion">{{ digestConclusion(activeDigest) }}</p>
      </section>

      <section class="detail-section">
        <h3>今日项目 / 内容变化</h3>
        <div v-if="activeProjects.length" class="rec-list">
          <article
            v-for="group in activeProjects"
            :key="`${group.repo || group.title}-${group.display_url}`"
            class="rec-item project-item"
          >
            <div class="rec-head">
              <strong>{{ group.title || group.repo || '未命名项目' }}</strong>
              <div class="tag-row">
                <el-tag v-for="tag in projectTags(group)" :key="`${group.title}-${tag}`" size="small" type="success">
                  {{ projectTagText(tag) }}
                </el-tag>
              </div>
            </div>
            <p class="rec-intro">{{ cleanDigestText(group.summary || '') || '暂无可读摘要，可查看来源文档。' }}</p>
            <p class="rec-count">涉及文档：{{ Number(group.documents_count || 0) }}，推荐文档：{{ Number(group.recommended_count || 0) }}</p>
            <div class="rec-meta">
              <span>来源：GitHub</span>
              <div class="rec-links">
                <a
                  v-if="projectLink(group)"
                  :href="projectLink(group)"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ projectLinkLabel(group) }}</a>
                <a
                  v-if="group.repository_url && group.repository_url !== projectLink(group)"
                  :href="group.repository_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >查看仓库</a>
                <a
                  v-if="projectDocs(group).length && projectDocs(group)[0].file_url"
                  :href="projectDocs(group)[0].file_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ ((projectDocs(group)[0].file_path || '').toLowerCase().endsWith('readme.md')) ? '查看README' : '查看文件' }}</a>
                <span v-if="!projectLink(group)">暂无可用链接</span>
              </div>
            </div>
            <ul v-if="projectDocs(group).length" class="doc-list">
              <li v-for="doc in projectDocs(group).slice(0, 4)" :key="`${group.title}-${doc.file_path}-${doc.title}`">
                {{ doc.file_path || doc.title || '未命名文档' }}：
                {{ cleanDigestText(doc.summary || '') || '暂无可读摘要。' }}
                <el-button
                  v-if="doc.source_document_id || doc.document_id"
                  size="small"
                  text
                  type="primary"
                  @click="openSourceDocument(doc)"
                >查看来源文档</el-button>
                <el-button size="small" text @click="copySummaryText(doc.summary || '')">复制摘要</el-button>
              </li>
            </ul>
          </article>
        </div>
        <el-empty v-else :description="noRecommendationReason(activeDigest)" />
      </section>

      <section class="detail-section metrics">
        <h3>同步概览</h3>
        <el-row :gutter="12">
          <el-col :span="8"><div class="metric">同步 source：{{ Number(activeStats.sources_synced || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">成功任务：{{ Number(activeStats.succeeded_jobs || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">失败任务：{{ Number(activeStats.failed_jobs || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">项目总数：{{ Number(activeStats.projects_total || activeProjects.length || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">新增项目：{{ Number(activeStats.projects_created || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">更新项目：{{ Number(activeStats.projects_updated || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">推荐项目：{{ Number(activeStats.projects_recommended || activeRecommendedProjects.length || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">新增文档：{{ Number(activeStats.documents_created || 0) }}</div></el-col>
          <el-col :span="8"><div class="metric">更新文档：{{ Number(activeStats.documents_updated || 0) }}</div></el-col>
        </el-row>
      </section>

      <section class="detail-section metrics minor">
        <h3>系统统计</h3>
        <el-row :gutter="12">
          <el-col :span="12"><div class="metric">新增内容分块：{{ Number(activeStats.chunks_created || 0) }}</div></el-col>
          <el-col :span="12"><div class="metric">完成向量化：{{ Number(activeStats.embedded_chunks || 0) }}</div></el-col>
          <el-col :span="12"><div class="metric">新增摘要：{{ Number(activeStats.summaries_created || 0) }}</div></el-col>
          <el-col :span="12"><div class="metric">新生成 Skill 草稿：{{ Number(activeStats.skill_candidates_created || 0) }}</div></el-col>
        </el-row>
      </section>

      <section v-if="activeFailedReasons.length" class="detail-section">
        <h3>失败任务</h3>
        <ol class="failed-list">
          <li v-for="(reason, idx) in activeFailedReasons.slice(0, 10)" :key="`err-${idx}`">{{ reason }}</li>
        </ol>
      </section>
    </div>

    <template #footer>
      <el-button @click="copyDigest">复制简报</el-button>
      <el-button @click="detailVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.digest-page {
  display: grid;
  gap: 14px;
}

.digest-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 12px;
}

.digest-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.digest-table-card {
  border: 1px solid #e7edf5;
  border-radius: 12px;
}

.list-shell {
  height: calc(100vh - 430px);
  max-height: calc(100vh - 370px);
  min-height: 260px;
  overflow: auto;
}

.digest-table :deep(.el-table__header th) {
  background: #f8fafc;
  color: #334155;
  font-weight: 600;
}

.digest-empty-tip {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
  max-width: 620px;
}

.digest-detail-body {
  max-height: 80vh;
  overflow-y: auto;
  display: grid;
  gap: 14px;
  padding-right: 4px;
}

.detail-section {
  border: 1px solid #e9eef5;
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}

.detail-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #0f172a;
}

.conclusion {
  margin: 0;
  color: #334155;
  line-height: 1.7;
}

.rec-list {
  display: grid;
  gap: 10px;
}

.rec-item {
  border: 1px solid #edf1f7;
  border-radius: 8px;
  padding: 10px;
  background: #f8fafc;
}

.rec-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.rec-intro {
  margin: 8px 0;
  color: #334155;
  line-height: 1.7;
}

.rec-meta {
  display: flex;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.rec-links {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.rec-meta a {
  color: #2563eb;
  text-decoration: none;
}

.rec-meta a:hover {
  text-decoration: underline;
}

.tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rec-count {
  margin: 4px 0 8px;
  color: #64748b;
  font-size: 12px;
}

.doc-list {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
}

.metrics .metric {
  background: #f8fafc;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  color: #334155;
}

.minor .metric {
  color: #64748b;
}

.muted {
  margin: 0;
  color: #64748b;
}

.failed-list {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .list-shell {
    height: auto;
    max-height: 65vh;
    min-height: 220px;
  }
}
</style>
