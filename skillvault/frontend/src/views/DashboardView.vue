<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'

const stats = ref({ sources: 0, documents: 0, chunks: 0, skills: 0, prompts: 0, jobs: [] as any[] })

async function load() {
  const { data } = await api.get('/api/dashboard')
  stats.value = data
}

onMounted(load)
</script>

<template>
  <h2>Dashboard</h2>
  <el-row :gutter="12">
    <el-col :span="4"><el-card>Sources: {{ stats.sources }}</el-card></el-col>
    <el-col :span="4"><el-card>Documents: {{ stats.documents }}</el-card></el-col>
    <el-col :span="4"><el-card>Chunks: {{ stats.chunks }}</el-card></el-col>
    <el-col :span="4"><el-card>Skills: {{ stats.skills }}</el-card></el-col>
    <el-col :span="4"><el-card>Prompts: {{ stats.prompts }}</el-card></el-col>
  </el-row>
  <el-table :data="stats.jobs" style="margin-top: 16px">
    <el-table-column prop="id" label="Job ID" width="90" />
    <el-table-column prop="job_type" label="Type" />
    <el-table-column prop="status" label="Status" />
    <el-table-column prop="error_message" label="Error" />
  </el-table>
</template>
