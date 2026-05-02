<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'

const sources = ref<any[]>([])
const latestJobBySource = ref<Record<number, any>>({})
const repoBySource = ref<Record<number, string>>({})
const form = reactive({ source_type: 'manual', name: '', url: '', owner: '', license: '', metadata: {} as Record<string, any> })
const loading = ref(false)
const creating = ref(false)
const rowLoading = reactive<Record<number, boolean>>({})
const overviewVisible = ref(false)
const activeOverview = ref<any>(null)
const { t } = useI18n()

async function load() {
  loading.value = true
  try {
    const [sourcesResp, jobsResp, reposResp] = await Promise.all([
      api.get('/api/sources'),
      api.get('/api/jobs'),
      api.get('/api/github/repos'),
    ])
    sources.value = sourcesResp.data

    const jobMap: Record<number, any> = {}
    for (const job of jobsResp.data || []) {
      if (job.job_type !== 'github_sync') continue
      const sourceId = Number(job?.payload?.source_id)
      if (!sourceId || jobMap[sourceId]) continue
      jobMap[sourceId] = job
    }
    latestJobBySource.value = jobMap

    const repoMap: Record<number, string> = {}
    for (const repo of reposResp.data || []) {
      if (repo?.source_id && !repoMap[repo.source_id]) {
        repoMap[repo.source_id] = repo.full_name
      }
    }
    repoBySource.value = repoMap
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || t('sources.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function createSource() {
  creating.value = true
  try {
    await api.post('/api/sources', form)
    form.name = ''
    form.url = ''
    await load()
    ElMessage.success('Source 创建成功')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || t('sources.sourceCreateFailed'))
  } finally {
    creating.value = false
  }
}

function formatDate(ts?: string) {
  if (!ts) return '-'
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
    ElMessage.error(error?.response?.data?.detail || t('sources.syncSettingsFailed'))
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
    ElMessage.error(error?.response?.data?.detail || t('sources.syncNowFailed'))
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
  <h2>{{ t('sources.title') }}</h2>
  <el-form inline>
    <el-form-item :label="t('sources.type')"><el-input v-model="form.source_type" /></el-form-item>
    <el-form-item :label="t('sources.name')"><el-input v-model="form.name" /></el-form-item>
    <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
    <el-button type="primary" :loading="creating" @click="createSource">{{ t('common.create') }}</el-button>
  </el-form>

  <el-table :data="sources" v-loading="loading" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="source_type" :label="t('sources.type')" />
    <el-table-column prop="name" :label="t('sources.name')" />
    <el-table-column prop="url" :label="t('sources.url')" />
    <el-table-column :label="t('sources.repo')" width="180">
      <template #default="scope">{{ repoBySource[scope.row.id] || '-' }}</template>
    </el-table-column>
    <el-table-column prop="license" :label="t('sources.license')" />
    <el-table-column :label="t('sources.autoSync')" width="130">
      <template #default="scope">
        <el-switch
          v-model="scope.row.auto_sync_enabled"
          :disabled="scope.row.source_type !== 'github_api' || rowLoading[scope.row.id]"
          @change="updateSyncSettings(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column :label="t('sources.syncInterval')" width="150">
      <template #default="scope">
        <el-input-number
          v-model="scope.row.sync_interval_minutes"
          :min="10"
          :step="10"
          :disabled="scope.row.source_type !== 'github_api' || rowLoading[scope.row.id]"
          @change="updateSyncSettings(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column :label="t('sources.lastSync')" width="180">
      <template #default="scope">{{ formatDate(scope.row.last_sync_at) }}</template>
    </el-table-column>
    <el-table-column :label="t('sources.nextSync')" width="180">
      <template #default="scope">{{ formatDate(scope.row.next_sync_at) }}</template>
    </el-table-column>
    <el-table-column :label="t('sources.status')" width="110">
      <template #default="scope">{{ sourceStatus(scope.row) }}</template>
    </el-table-column>
    <el-table-column :label="t('sources.error')" min-width="240">
      <template #default="scope">{{ sourceError(scope.row) }}</template>
    </el-table-column>
    <el-table-column :label="t('common.actions')" width="220">
      <template #default="scope">
        <el-button size="small" @click="openOverview(scope.row)">{{ t('sources.viewOverview') }}</el-button>
        <el-button
          size="small"
          type="primary"
          :disabled="scope.row.source_type !== 'github_api'"
          :loading="rowLoading[scope.row.id]"
          @click="syncNow(scope.row)"
        >
          {{ t('sources.syncNow') }}
        </el-button>
      </template>
    </el-table-column>
  </el-table>

  <el-dialog v-model="overviewVisible" :title="t('sources.overview')" width="900px">
    <div v-if="activeOverview" style="display:grid; gap:12px">
      <div><b>{{ t('sources.name') }}：</b>{{ activeOverview.name }}</div>
      <div><b>URL：</b>{{ activeOverview.url }}</div>
      <div><b>{{ t('sources.overview') }}：</b></div>
      <pre style="white-space:pre-wrap; word-break:break-word; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:12px; max-height:40vh; overflow:auto">{{ activeOverview?.metadata?.overview || '-' }}</pre>
      <div><b>{{ t('sources.recommendedDocuments') }}：</b></div>
      <el-table :data="activeOverview?.metadata?.recommended_documents || []" size="small">
        <el-table-column prop="file_path" label="File" min-width="220" />
        <el-table-column prop="language" label="Lang" width="90" />
        <el-table-column prop="reason" label="Reason" min-width="220" />
      </el-table>
      <div><b>{{ t('sources.lastSyncStats') }}：</b> {{ JSON.stringify(activeOverview?.metadata?.last_sync_stats || {}, null, 2) }}</div>
    </div>
  </el-dialog>
</template>
