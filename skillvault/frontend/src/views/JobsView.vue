<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const jobs = ref<any[]>([])
const filterJobType = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)
const { t } = useI18n()

async function load() {
  const params: Record<string, any> = {
    page: currentPage.value,
    page_size: pageSize.value,
  }
  if (filterJobType.value) params.job_type = filterJobType.value
  if (filterStatus.value) params.status = filterStatus.value
  const { data } = await api.get('/api/jobs', { params })
  jobs.value = Array.isArray(data) ? data : (data.items || [])
  total.value = Array.isArray(data) ? jobs.value.length : Number(data.total || 0)
  if (currentPage.value > 1 && jobs.value.length === 0 && total.value > 0) {
    currentPage.value -= 1
    await load()
  }
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

function statusLabel(status?: string) {
  const key = status || 'unknown'
  const mapped = t(`status.${key}`)
  return mapped === `status.${key}` ? t('status.unknown') : mapped
}

function jobTypeLabel(type?: string) {
  const key = type || 'unknown'
  const mapped = t(`jobTypes.${key}`)
  return mapped === `jobTypes.${key}` ? t('jobTypes.unknown') : mapped
}

watch([filterJobType, filterStatus], async () => {
  currentPage.value = 1
  await load()
})

const filteredJobs = computed(() => jobs.value)

onMounted(load)
</script>

<template>
  <section>
    <el-card shadow="never" class="jobs-panel">
      <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
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
          <el-option :label="t('status.cancelled')" value="cancelled" />
          <el-option :label="t('status.timeout')" value="timeout" />
        </el-select>
        <el-button @click="load">{{ t('common.refresh') }}</el-button>
      </div>

      <div class="list-shell">
        <el-table :data="filteredJobs" height="100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column :label="t('jobs.type')" width="140"><template #default="scope">{{ jobTypeLabel(scope.row.job_type) }}</template></el-table-column>
        <el-table-column :label="t('jobs.status')" width="120"><template #default="scope">{{ statusLabel(scope.row.status) }}</template></el-table-column>
        <el-table-column :label="t('jobs.created')" width="170"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column>
        <el-table-column :label="t('jobs.started')" width="170"><template #default="scope">{{ formatDate(scope.row.started_at) }}</template></el-table-column>
        <el-table-column :label="t('jobs.finished')" width="170"><template #default="scope">{{ formatDate(scope.row.finished_at) }}</template></el-table-column>
        <el-table-column :label="t('jobs.payload')" min-width="280"><template #default="scope">{{ payloadSummary(scope.row.payload) }}</template></el-table-column>
        <el-table-column prop="retry_count" :label="t('jobs.retry')" width="80" />
        <el-table-column prop="error_message" :label="t('jobs.error')" min-width="260" />
        <el-table-column :label="t('common.actions')" width="120">
          <template #default="scope"><el-button size="small" @click="retryJob(scope.row.id)">{{ t('jobs.retry') }}</el-button></template>
        </el-table-column>
        <template #empty><el-empty :description="t('jobs.emptyDesc')" /></template>
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
</template>

<style scoped>
.jobs-panel { display: flex; flex-direction: column; }
.list-shell {
  height: calc(100vh - 440px);
  max-height: calc(100vh - 390px);
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
