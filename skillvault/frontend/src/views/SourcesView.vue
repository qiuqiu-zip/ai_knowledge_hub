<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const sources = ref<any[]>([])
const latestJobBySource = ref<Record<number, any>>({})
const repoBySource = ref<Record<number, string>>({})
const form = reactive({ source_type: 'github_api', name: '', url: '', owner: '', license: '', metadata: {} as Record<string, any> })
const loading = ref(false)
const creating = ref(false)
const rowLoading = reactive<Record<number, boolean>>({})
const overviewVisible = ref(false)
const activeOverview = ref<any>(null)
const { t, locale } = useI18n()
const pagination = reactive({ page: 1, pageSize: 5, total: 0 })

const githubSources = computed(() => sources.value.filter((s) => s.source_type === 'github_api'))
const otherSources = computed(() => sources.value.filter((s) => s.source_type !== 'github_api'))

function normalizeListResponse(data: any) {
  if (Array.isArray(data)) return { items: data, total: data.length }
  if (data && Array.isArray(data.items)) return { items: data.items, total: Number(data.total ?? data.items.length) }
  return { items: [], total: 0 }
}

function getErrorMessage(error: any, fallback = '操作失败，请稍后重试') {
  const detail = error?.response?.data?.detail
  const message = error?.response?.data?.message
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((x) => (typeof x === 'string' ? x : x?.msg || x?.message || JSON.stringify(x)))
      .filter(Boolean)
      .join('；')
  }
  if (detail && typeof detail === 'object') return detail?.msg || detail?.message || JSON.stringify(detail)
  if (typeof message === 'string' && message.trim()) return message
  if (error?.message) return String(error.message)
  return fallback
}

async function load() {
  loading.value = true
  try {
    const sourcesResp = await api.get('/api/sources', { params: { page: pagination.page, page_size: pagination.pageSize } })
    const normalizedSources = normalizeListResponse(sourcesResp.data)
    sources.value = normalizedSources.items
    pagination.total = normalizedSources.total

    try {
      const jobsResp = await api.get('/api/jobs', { params: { page: 1, page_size: 100 } })
      const normalizedJobs = normalizeListResponse(jobsResp.data)
      const jobMap: Record<number, any> = {}
      for (const job of normalizedJobs.items || []) {
        if (job.job_type !== 'github_sync') continue
        const sourceId = Number(job?.payload?.source_id)
        if (!sourceId || jobMap[sourceId]) continue
        jobMap[sourceId] = job
      }
      latestJobBySource.value = jobMap
    } catch (error: any) {
      console.error('[sources] load jobs failed', error)
      latestJobBySource.value = {}
      ElMessage.warning(`部分同步状态加载失败：${getErrorMessage(error, '请稍后刷新重试')}`)
    }

    try {
      const reposResp = await api.get('/api/github/repos')
      const normalizedRepos = normalizeListResponse(reposResp.data)
      const repoMap: Record<number, string> = {}
      for (const repo of normalizedRepos.items || []) {
        if (repo?.source_id && !repoMap[repo.source_id]) {
          repoMap[repo.source_id] = repo.full_name
        }
      }
      repoBySource.value = repoMap
    } catch (error: any) {
      console.error('[sources] load github repos failed', error)
      repoBySource.value = {}
      ElMessage.warning(`仓库映射加载失败：${getErrorMessage(error, '来源列表仍可使用')}`)
    }
  } catch (error: any) {
    console.error('[sources] load sources failed', error)
    ElMessage.error(getErrorMessage(error, t('sources.loadFailed')))
  } finally {
    loading.value = false
  }
  if (pagination.page > 1 && sources.value.length === 0 && pagination.total > 0) {
    pagination.page -= 1
    await load()
  }
}

function inferRepoNameFromUrl(url: string) {
  try {
    const matched = url.trim().match(/^https?:\/\/github\.com\/([^/]+)\/([^/#?]+)\/?/i)
    if (!matched) return ''
    return `${matched[1]}/${matched[2]}`
  } catch {
    return ''
  }
}

async function createSource() {
  creating.value = true
  try {
    const payload = {
      ...form,
      source_type: 'github_api',
      name: form.name.trim() || inferRepoNameFromUrl(form.url),
      url: form.url.trim(),
    }
    await api.post('/api/sources', payload)
    form.name = ''
    form.url = ''
    form.owner = ''
    form.license = ''
    await load()
    ElMessage.success(t('sources.sourceCreated'))
  } catch (error: any) {
    console.error(error)
    ElMessage.error(getErrorMessage(error, t('sources.sourceCreateFailed')))
  } finally {
    creating.value = false
  }
}

function formatDate(ts?: string) {
  if (!ts) return locale.value === 'zh-CN' ? '暂无计划' : 'Not scheduled'
  return new Date(ts).toLocaleString()
}

function sourceStatus(row: any) {
  const job = latestJobBySource.value[row.id]
  return job?.status ? t(`status.${job.status}`) : '-'
}

function sourceError(row: any) {
  const job = latestJobBySource.value[row.id]
  return job?.error_message || '-'
}

function sourceTypeLabel(sourceType: string) {
  const key = sourceType || 'unknown'
  const mapped = t(`sourceTypes.${key}`)
  return mapped === `sourceTypes.${key}` ? t('sourceTypes.unknown') : mapped
}

function sourceDisplayName(row: any) {
  return repoBySource.value[row.id] || row.name || inferRepoNameFromUrl(row.url || '') || `source-${row.id}`
}

function repositoryUrl(row: any) {
  const rowRepoUrl = typeof row?.repository_url === 'string' ? row.repository_url.trim() : ''
  if (rowRepoUrl) return rowRepoUrl
  const metadataRepoUrl = typeof row?.metadata?.repository_url === 'string' ? row.metadata.repository_url.trim() : ''
  if (metadataRepoUrl) return metadataRepoUrl
  const repo = repoBySource.value[row.id] || inferRepoNameFromUrl(row.url || '')
  if (repo) return `https://github.com/${repo}`
  if (typeof row?.url === 'string' && row.url.trim()) return row.url.trim()
  if (typeof row?.source_url === 'string' && row.source_url.trim()) return row.source_url.trim()
  return ''
}

function sourceLinkLabel(row: any) {
  const url = repositoryUrl(row)
  return url.includes('github.com') ? t('sources.openRepo') : t('sources.openSource')
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

function openSourceLink(row: any) {
  const url = repositoryUrl(row)
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

function licenseLabel(row: any) {
  return row.license || t('sources.licenseUnknown')
}

function syncIntervalLabel(value?: number) {
  if (!value) return '-'
  return t('sources.syncEveryMinutes', { minutes: value })
}

async function updateSyncSettings(row: any) {
  if (row.source_type !== 'github_api') return
  rowLoading[row.id] = true
  try {
    await api.put(`/api/sources/${row.id}/sync-settings`, {
      auto_sync_enabled: !!row.auto_sync_enabled,
      sync_interval_minutes: Number(row.sync_interval_minutes || 1440),
    })
    await load()
    ElMessage.success(t('sources.syncSettingsUpdated'))
  } catch (error: any) {
    console.error(error)
    ElMessage.error(getErrorMessage(error, t('sources.syncSettingsFailed')))
  } finally {
    rowLoading[row.id] = false
  }
}

async function syncNow(row: any) {
  if (row.source_type !== 'github_api') return
  rowLoading[row.id] = true
  try {
    const { data } = await api.post(`/api/sources/${row.id}/sync-now`)
    ElMessage.success(t('sources.syncNowCreated', { id: data.job_id }))
    await load()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(getErrorMessage(error, t('sources.syncNowFailed')))
  } finally {
    rowLoading[row.id] = false
  }
}

function openOverview(row: any) {
  activeOverview.value = row
  overviewVisible.value = true
}

onMounted(load)
</script>

<template>
  <section class="sources-page">
    <el-card class="create-card" shadow="never">
      <template #header>
        <div class="create-header">
          <div class="create-title">{{ t('sources.addGithubSource') }}</div>
          <div class="create-desc">{{ t('sources.addGithubSourceDesc') }}</div>
        </div>
      </template>

      <el-form class="create-form" label-position="top">
        <el-form-item :label="t('sources.type')">
          <el-input :model-value="t('sources.typeGithub')" disabled />
        </el-form-item>
        <el-form-item :label="t('sources.nameOptional')">
          <el-input v-model="form.name" :placeholder="t('sources.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('sources.githubUrl')" class="url-item">
          <el-input v-model="form.url" :placeholder="t('sources.githubUrlPlaceholder')" />
        </el-form-item>
        <div class="create-actions">
          <el-button type="primary" :loading="creating" @click="createSource">{{ t('sources.addSource') }}</el-button>
        </div>
      </el-form>
    </el-card>

    <div class="source-list-shell">
      <div v-loading="loading" class="source-list">
        <el-empty v-if="!githubSources.length && !otherSources.length" :description="t('sources.emptyDesc')" />

        <template v-else>
          <el-card v-for="row in githubSources" :key="row.id" class="source-card" shadow="never">
          <div class="card-top">
            <div>
              <div class="source-name">{{ sourceDisplayName(row) }}</div>
              <div class="source-meta">
                <el-tag size="small" type="info">{{ sourceTypeLabel(row.source_type) }}</el-tag>
                <span class="license">{{ t('sources.license') }}: {{ licenseLabel(row) }}</span>
              </div>
            </div>
            <div class="card-links">
              <el-button size="small" plain @click="openSourceLink(row)">{{ sourceLinkLabel(row) }}</el-button>
              <el-button size="small" @click="openOverview(row)">{{ t('sources.viewOverview') }}</el-button>
              <el-button
                size="small"
                type="primary"
                :loading="rowLoading[row.id]"
                @click="syncNow(row)"
              >
                {{ t('sources.syncNow') }}
              </el-button>
            </div>
          </div>

          <div class="card-grid">
            <div class="item">
              <div class="label">{{ t('sources.autoSync') }}</div>
              <div class="value sync-inline">
                <el-switch
                  v-model="row.auto_sync_enabled"
                  :disabled="row.source_type !== 'github_api' || rowLoading[row.id]"
                  @change="updateSyncSettings(row)"
                />
                <span>{{ row.auto_sync_enabled ? t('sources.syncEnabled') : t('sources.syncDisabled') }}</span>
              </div>
            </div>

            <div class="item">
              <div class="label">{{ t('sources.syncInterval') }}</div>
              <div class="value sync-inline">
                <el-input-number
                  v-model="row.sync_interval_minutes"
                  :min="10"
                  :step="10"
                  :disabled="row.source_type !== 'github_api' || rowLoading[row.id]"
                  @change="updateSyncSettings(row)"
                />
                <span>{{ syncIntervalLabel(row.sync_interval_minutes) }}</span>
              </div>
            </div>

            <div class="item">
              <div class="label">{{ t('sources.lastSync') }}</div>
              <div class="value">{{ row.last_sync_at ? formatDate(row.last_sync_at) : t('sources.neverSynced') }}</div>
            </div>

            <div class="item">
              <div class="label">{{ t('sources.nextSync') }}</div>
              <div class="value">{{ row.next_sync_at ? formatDate(row.next_sync_at) : t('sources.noSchedule') }}</div>
            </div>

            <div class="item">
              <div class="label">{{ t('sources.status') }}</div>
              <div class="value">{{ sourceStatus(row) }}</div>
            </div>

            <div class="item full-width">
              <div class="label">{{ t('sources.error') }}</div>
              <div class="value error-msg">{{ sourceError(row) }}</div>
            </div>
          </div>
          </el-card>

          <el-card v-if="otherSources.length" class="source-card" shadow="never">
            <template #header>
              <div class="source-name">{{ t('sources.otherSources') }}</div>
            </template>
            <el-table :data="otherSources" size="small">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column :label="t('sources.type')">
                <template #default="scope">{{ sourceTypeLabel(scope.row.source_type) }}</template>
              </el-table-column>
              <el-table-column prop="name" :label="t('sources.name')" />
              <el-table-column prop="url" :label="t('sources.url')" />
            </el-table>
          </el-card>
        </template>
      </div>
    </div>
    <PaginationBar
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :page-sizes="[5, 10, 20, 50]"
      :total="pagination.total"
      @update:current-page="load"
      @update:page-size="load"
    />

    <el-dialog v-model="overviewVisible" :title="t('sources.overview')" width="900px">
      <div v-if="activeOverview" style="display:grid; gap:12px">
        <div><b>{{ t('sources.name') }}：</b>{{ activeOverview.name }}</div>
        <div><b>{{ t('sources.url') }}：</b>{{ activeOverview.url }}</div>
        <div><b>{{ t('sources.overview') }}：</b></div>
        <pre style="white-space:pre-wrap; word-break:break-word; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:12px; max-height:40vh; overflow:auto">{{ activeOverview?.metadata?.overview || '-' }}</pre>
        <div><b>{{ t('sources.recommendedDocuments') }}：</b></div>
        <el-table :data="activeOverview?.metadata?.recommended_documents || []" size="small">
          <el-table-column prop="file_path" label="文件" min-width="220" />
          <el-table-column prop="language" label="语言" width="90" />
          <el-table-column prop="reason" label="推荐原因" min-width="220" />
        </el-table>
        <div><b>{{ t('sources.lastSyncStats') }}：</b> {{ JSON.stringify(activeOverview?.metadata?.last_sync_stats || {}, null, 2) }}</div>
      </div>
    </el-dialog>
  </section>
</template>

<style scoped>
.sources-page {
  display: grid;
  gap: 16px;
}

.create-card {
  border: 1px solid #e5e7eb;
}

.create-header {
  display: grid;
  gap: 4px;
}

.create-title {
  font-size: 16px;
  font-weight: 600;
}

.create-desc {
  color: #6b7280;
  font-size: 13px;
}

.create-form {
  display: grid;
  grid-template-columns: 180px 1fr 2fr auto;
  gap: 12px;
  align-items: end;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.create-actions {
  display: flex;
  align-items: flex-end;
  height: 100%;
}

.source-list {
  display: grid;
  gap: 12px;
  min-height: 220px;
}

.source-list-shell {
  height: calc(100vh - 420px);
  max-height: calc(100vh - 360px);
  min-height: 280px;
  overflow: auto;
}

.source-card {
  border: 1px solid #e5e7eb;
}

.card-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.source-name {
  font-size: 17px;
  font-weight: 600;
  color: #111827;
}

.source-meta {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  align-items: center;
  color: #6b7280;
  font-size: 13px;
}

.card-links {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 12px 20px;
}

.item {
  display: grid;
  gap: 6px;
}

.item.full-width {
  grid-column: 1 / -1;
}

.label {
  font-size: 12px;
  color: #6b7280;
}

.value {
  font-size: 14px;
  color: #111827;
}

.error-msg {
  color: #b91c1c;
}

.sync-inline {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

@media (max-width: 1200px) {
  .create-form {
    grid-template-columns: 1fr 1fr;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .create-form {
    grid-template-columns: 1fr;
  }

  .card-top {
    flex-direction: column;
  }

  .source-list-shell {
    height: auto;
    max-height: 65vh;
    min-height: 240px;
  }
}
</style>
