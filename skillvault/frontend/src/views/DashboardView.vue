<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'
import { useI18n } from 'vue-i18n'

const stats = ref({ sources: 0, documents: 0, chunks: 0, skills: 0, prompts: 0, jobs: [] as any[] })
const { t } = useI18n()

async function load() {
  const { data } = await api.get('/api/dashboard')
  stats.value = data
}

onMounted(load)
</script>

<template>
  <h2>{{ t('dashboard.title') }}</h2>
  <el-row :gutter="12">
    <el-col :span="4"><el-card>{{ t('dashboard.sources') }}: {{ stats.sources }}</el-card></el-col>
    <el-col :span="4"><el-card>{{ t('dashboard.documents') }}: {{ stats.documents }}</el-card></el-col>
    <el-col :span="4"><el-card>{{ t('dashboard.chunks') }}: {{ stats.chunks }}</el-card></el-col>
    <el-col :span="4"><el-card>{{ t('dashboard.skills') }}: {{ stats.skills }}</el-card></el-col>
    <el-col :span="4"><el-card>{{ t('dashboard.prompts') }}: {{ stats.prompts }}</el-card></el-col>
  </el-row>
  <h3 style="margin-top: 16px">{{ t('dashboard.recentJobs') }}</h3>
  <el-table :data="stats.jobs" style="margin-top: 16px">
    <el-table-column prop="id" :label="t('dashboard.jobId')" width="90" />
    <el-table-column prop="job_type" :label="t('common.type')" />
    <el-table-column prop="status" :label="t('common.status')" />
    <el-table-column prop="error_message" :label="t('dashboard.error')" />
  </el-table>
</template>
