<script setup lang="ts">
import { ref } from 'vue'
import api from '../api/client'

const repoUrl = ref('https://github.com/langchain-ai/langchain')
const jobId = ref<number | null>(null)
const job = ref<any>(null)

async function submit() {
  const { data } = await api.post('/api/github/import', { repo_url: repoUrl.value })
  jobId.value = data.job_id
}

async function queryJob() {
  if (!jobId.value) return
  const { data } = await api.get(`/api/jobs/${jobId.value}`)
  job.value = data
}
</script>

<template>
  <h2>GitHub Import</h2>
  <el-input v-model="repoUrl" placeholder="https://github.com/owner/repo" />
  <div style="margin-top: 12px">
    <el-button type="primary" @click="submit">Import</el-button>
    <el-button @click="queryJob" :disabled="!jobId">Check Job</el-button>
  </div>
  <p v-if="jobId">job_id: {{ jobId }}</p>
  <pre v-if="job">{{ JSON.stringify(job, null, 2) }}</pre>
</template>
