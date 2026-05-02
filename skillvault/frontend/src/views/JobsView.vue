<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api/client'

const jobs = ref<any[]>([])
const filterJobType = ref('')
const filterStatus = ref('')
const { t } = useI18n()

async function load() {
  const { data } = await api.get('/api/jobs')
  jobs.value = data
}

async function retryJob(id: number) {
  await api.post(`/api/jobs/${id}/retry`)
  await load()
}

function formatDate(ts?: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

function payloadSummary(payload: any) {
  if (!payload || typeof payload !== 'object') return '-'
  const parts: string[] = []
  if (payload.source_id !== undefined) parts.push(`source=${payload.source_id}`)
  if (payload.document_id !== undefined) parts.push(`doc=${payload.document_id}`)
  if (payload.repo_full_name) parts.push(`repo=${payload.repo_full_name}`)
  if (payload.repo_url) parts.push(`url=${payload.repo_url}`)
  return parts.length ? parts.join(' | ') : JSON.stringify(payload)
}

const filteredJobs = computed(() =>
  jobs.value.filter((job) => {
    const typeOk = !filterJobType.value || job.job_type === filterJobType.value
    const statusOk = !filterStatus.value || job.status === filterStatus.value
    return typeOk && statusOk
  }),
)

onMounted(load)
</script>

<template>
  <h2>{{ t('jobs.title') }}</h2>
  <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 12px">
    <el-select v-model="filterJobType" clearable :placeholder="t('jobs.filterJobType')" style="width: 180px">
      <el-option :label="t('jobTypes.github_sync')" value="github_sync" />
      <el-option :label="t('jobTypes.document_chunk')" value="document_chunk" />
      <el-option :label="t('jobTypes.document_embed')" value="document_embed" />
      <el-option :label="t('jobTypes.summarize')" value="summarize" />
      <el-option :label="t('jobTypes.skill_generate')" value="skill_generate" />
      <el-option :label="t('jobTypes.daily_digest')" value="daily_digest" />
    </el-select>
    <el-select v-model="filterStatus" clearable :placeholder="t('jobs.filterStatus')" style="width: 160px">
      <el-option :label="t('status.pending')" value="pending" />
      <el-option :label="t('status.running')" value="running" />
      <el-option :label="t('status.success')" value="success" />
      <el-option :label="t('status.failed')" value="failed" />
    </el-select>
    <el-button @click="load">{{ t('common.refresh') }}</el-button>
  </div>
  <el-table :data="filteredJobs" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column :label="t('jobs.type')" width="140">
      <template #default="scope">{{ jobTypeLabel(scope.row.job_type) }}</template>
    </el-table-column>
    <el-table-column :label="t('jobs.status')" width="120">
      <template #default="scope">{{ statusLabel(scope.row.status) }}</template>
    </el-table-column>
    <el-table-column :label="t('jobs.created')" width="170">
      <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
    </el-table-column>
    <el-table-column :label="t('jobs.started')" width="170">
      <template #default="scope">{{ formatDate(scope.row.started_at) }}</template>
    </el-table-column>
    <el-table-column :label="t('jobs.finished')" width="170">
      <template #default="scope">{{ formatDate(scope.row.finished_at) }}</template>
    </el-table-column>
    <el-table-column :label="t('jobs.payload')" min-width="280">
      <template #default="scope">{{ payloadSummary(scope.row.payload) }}</template>
    </el-table-column>
    <el-table-column prop="retry_count" :label="t('jobs.retry')" width="80" />
    <el-table-column prop="error_message" :label="t('jobs.error')" min-width="260" />
    <el-table-column :label="t('common.actions')" width="120">
      <template #default="scope">
        <el-button size="small" @click="retryJob(scope.row.id)">{{ t('jobs.retry') }}</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
function statusLabel(status?: string) {
  return t(`status.${status || 'unknown'}`)
}

function jobTypeLabel(type?: string) {
  return t(`jobTypes.${type || 'github_sync'}`)
}
