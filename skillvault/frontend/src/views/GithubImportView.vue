<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const repoUrl = ref('https://github.com/langchain-ai/langchain')
const jobId = ref<number | null>(null)
const job = ref<any>(null)
const repos = ref<any[]>([])
const reposLoading = ref(false)
const discovering = ref(false)
const discoveryResult = ref<any | null>(null)
const currentPage = ref(1)
const pageSize = ref(5)
const minStars = ref(100)
const preferChinese = ref(true)

function containsChinese(text: string) {
  return /[\u4e00-\u9fff]/.test(text || '')
}

function isChineseFriendly(repo: any) {
  const fullName = String(repo?.full_name || '')
  const description = String(repo?.description || '')
  const topics = Array.isArray(repo?.topics) ? repo.topics.join(' ') : ''
  return containsChinese(`${fullName} ${description} ${topics}`)
}

function starScore(repo: any) {
  const stars = Number(repo?.stars || 0)
  if (!preferChinese.value) return stars
  return stars + (isChineseFriendly(repo) ? Math.min(100, Math.floor(stars * 0.1) + 20) : 0)
}

const filteredRepos = computed(() => {
  return (repos.value || [])
    .filter((x) => Number(x?.stars || 0) >= Number(minStars.value || 0))
    .sort((a, b) => {
      const starsDiff = Number(b?.stars || 0) - Number(a?.stars || 0)
      if (Math.abs(starsDiff) > Math.max(10, Math.floor((Number(a?.stars || 0) + Number(b?.stars || 0)) * 0.2))) {
        return starsDiff
      }
      return starScore(b) - starScore(a)
    })
})

const pagedRepos = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRepos.value.slice(start, start + pageSize.value)
})

async function loadRepos() {
  reposLoading.value = true
  try {
    const { data } = await api.get('/api/github/repos')
    repos.value = Array.isArray(data) ? data : []
    if (currentPage.value > 1 && pagedRepos.value.length === 0 && filteredRepos.value.length > 0) {
      currentPage.value -= 1
    }
  } finally {
    reposLoading.value = false
  }
}

async function submit() {
  try {
    const { data } = await api.post('/api/github/import', { repo_url: repoUrl.value })
    jobId.value = data.job_id
    ElMessage.success(`任务已创建：job_id=${data.job_id}`)
    await loadRepos()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '导入失败')
  }
}

async function queryJob() {
  if (!jobId.value) return
  const { data } = await api.get(`/api/jobs/${jobId.value}`)
  job.value = data
}

function formatDiscoveryMessage(result: any) {
  if (!result) return ''
  if (typeof result?.message === 'string' && result.message.trim()) return result.message
  return `发现完成：新增 ${result?.created_sources || 0} 个来源，入队 ${result?.enqueued_jobs || 0} 个同步任务。`
}

async function discoverNow() {
  discovering.value = true
  try {
    const { data } = await api.post('/api/github/discover-now')
    discoveryResult.value = data || {}
    ElMessage.success(formatDiscoveryMessage(data))
    await loadRepos()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || '触发发现失败，请稍后重试'
    ElMessage.error(detail)
  } finally {
    discovering.value = false
  }
}

onMounted(loadRepos)
</script>

<template>
  <section class="github-import-page">
    <el-card shadow="never" class="intro">
      <p>批量发现和导入 GitHub 仓库，导入后会进入来源管理并参与后续自动同步。</p>
      <p class="tip">系统将基于仓库内容沉淀文档、每日简报、知识检索和 Skill 草稿。</p>
    </el-card>

    <el-card shadow="never">
      <el-form label-position="top">
        <el-form-item label="GitHub 仓库 URL">
          <el-input v-model="repoUrl" placeholder="https://github.com/owner/repo" />
        </el-form-item>
        <el-space>
          <el-button type="primary" @click="submit">导入仓库</el-button>
          <el-button @click="queryJob" :disabled="!jobId">查看任务状态</el-button>
        </el-space>
      </el-form>
      <p v-if="jobId" class="job-id">job_id: {{ jobId }}</p>
      <pre v-if="job" class="job-json">{{ JSON.stringify(job, null, 2) }}</pre>
    </el-card>

    <el-card shadow="never" class="discovery-card">
      <div class="discovery-head">
        <div>
          <div class="discovery-title">立即发现 GitHub 项目</div>
          <div class="discovery-desc">按 Star 优先、中文友好优先自动发现项目，并加入同步队列。</div>
        </div>
        <el-button type="primary" :loading="discovering" @click="discoverNow">立即发现 GitHub 项目</el-button>
      </div>

      <div v-if="discoveryResult" class="discovery-result">
        <div class="result-line">{{ formatDiscoveryMessage(discoveryResult) }}</div>
        <el-row :gutter="12" class="result-grid">
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">关键词数：{{ (discoveryResult.queries || []).length }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">拉取仓库：{{ discoveryResult.fetched || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">过滤数量：{{ discoveryResult.filtered || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">新增来源：{{ discoveryResult.created_sources || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">已存在来源：{{ discoveryResult.existing_sources || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">入队同步任务：{{ discoveryResult.enqueued_jobs || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="8"><div class="result-item">跳过重复任务：{{ discoveryResult.skipped_jobs || 0 }}</div></el-col>
          <el-col :xs="24" :sm="12" :md="16"><div class="result-item">限流状态：{{ discoveryResult?.rate_limit?.limited ? `是（${discoveryResult?.rate_limit?.message || '请稍后重试'}）` : '否' }}</div></el-col>
        </el-row>
      </div>
    </el-card>

    <el-card shadow="never" class="repos-card">
      <div class="repos-toolbar">
        <div class="toolbar-left">
          <strong>项目优先级</strong>
          <span class="toolbar-tip">优先展示高 Star 项目，其次中文友好项目</span>
        </div>
        <el-space>
          <span class="filter-label">最低 Star 数</span>
          <el-input-number v-model="minStars" :min="0" :step="50" @change="currentPage = 1" />
          <el-switch v-model="preferChinese" active-text="中文优先" @change="currentPage = 1" />
          <el-button :loading="reposLoading" @click="loadRepos">刷新</el-button>
        </el-space>
      </div>

      <div class="list-shell" v-loading="reposLoading">
        <el-table :data="pagedRepos" height="100%">
          <el-table-column prop="full_name" label="仓库" min-width="220" />
          <el-table-column prop="description" label="简介" min-width="320" />
          <el-table-column prop="stars" label="Star" width="100" />
          <el-table-column prop="language" label="语言" width="100" />
          <el-table-column label="中文友好" width="110">
            <template #default="scope">
              <el-tag v-if="isChineseFriendly(scope.row)" size="small" type="success">中文友好</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-link :href="scope.row.html_url" target="_blank" rel="noopener noreferrer">查看仓库</el-link>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无仓库记录，先导入一个 GitHub 仓库试试。" /></template>
        </el-table>
      </div>

      <PaginationBar
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="filteredRepos.length"
        :page-sizes="[5, 10, 20, 50]"
      />
    </el-card>
  </section>
</template>

<style scoped>
.github-import-page { display: grid; gap: 12px; }
.intro p { margin: 8px 0 0; color: #374151; }
.tip { font-size: 13px; color: #6b7280; }
.job-id { margin-top: 10px; color: #334155; }
.job-json { margin-top: 8px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
.repos-card { display: flex; flex-direction: column; }
.discovery-card { display: grid; gap: 10px; }
.discovery-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.discovery-title { font-size: 16px; font-weight: 600; color: #111827; }
.discovery-desc { color: #6b7280; font-size: 13px; margin-top: 4px; }
.discovery-result { border: 1px solid #e5e7eb; background: #f8fafc; border-radius: 8px; padding: 10px; display: grid; gap: 8px; }
.result-line { color: #0f172a; font-size: 14px; }
.result-grid { margin-top: 4px; }
.result-item { color: #334155; font-size: 13px; line-height: 1.6; }
.repos-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.toolbar-left { display: flex; flex-direction: column; gap: 3px; }
.toolbar-tip { color: #64748b; font-size: 12px; }
.filter-label { color: #64748b; font-size: 12px; }
.list-shell { height: calc(100vh - 500px); max-height: calc(100vh - 430px); min-height: 240px; overflow: auto; }
@media (max-width: 960px) {
  .list-shell { height: auto; max-height: 60vh; min-height: 220px; }
}
</style>
