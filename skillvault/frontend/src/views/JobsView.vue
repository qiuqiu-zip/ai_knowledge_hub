<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'

const jobs = ref<any[]>([])

async function load() {
  const { data } = await api.get('/api/jobs')
  jobs.value = data
}

async function retryJob(id: number) {
  await api.post(`/api/jobs/${id}/retry`)
  await load()
}

onMounted(load)
</script>

<template>
  <h2>Jobs</h2>
  <el-button @click="load">Refresh</el-button>
  <el-table :data="jobs" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="job_type" label="Type" width="140" />
    <el-table-column prop="status" label="Status" width="120" />
    <el-table-column prop="retry_count" label="Retry" width="80" />
    <el-table-column prop="error_message" label="Error" />
    <el-table-column label="Action" width="120">
      <template #default="scope">
        <el-button size="small" @click="retryJob(scope.row.id)">Retry</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
