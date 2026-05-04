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
  <section class="dashboard-page">
    <el-card class="hero" shadow="never">
      <h2>{{ t('dashboard.heroTitle') }}</h2>
      <p>{{ t('dashboard.heroSubtitle') }}</p>
      <p class="hero-flow">{{ t('dashboard.heroFlow') }}</p>
    </el-card>

    <el-row :gutter="12" class="stat-row">
      <el-col :span="4"><el-card shadow="never">{{ t('dashboard.sources') }}: {{ stats.sources }}</el-card></el-col>
      <el-col :span="4"><el-card shadow="never">{{ t('dashboard.documents') }}: {{ stats.documents }}</el-card></el-col>
      <el-col :span="4"><el-card shadow="never">{{ t('dashboard.chunks') }}: {{ stats.chunks }}</el-card></el-col>
      <el-col :span="4"><el-card shadow="never">{{ t('dashboard.skills') }}: {{ stats.skills }}</el-card></el-col>
      <el-col :span="4"><el-card shadow="never">{{ t('dashboard.prompts') }}: {{ stats.prompts }}</el-card></el-col>
    </el-row>

    <el-card shadow="never" class="flow-card">
      <template #header>{{ t('dashboard.productFlow') }}</template>
      <el-steps :active="4" finish-status="success">
        <el-step :title="t('dashboard.step1Title')" :description="t('dashboard.step1Desc')" />
        <el-step :title="t('dashboard.step2Title')" :description="t('dashboard.step2Desc')" />
        <el-step :title="t('dashboard.step3Title')" :description="t('dashboard.step3Desc')" />
        <el-step :title="t('dashboard.step4Title')" :description="t('dashboard.step4Desc')" />
      </el-steps>
    </el-card>

    <h3 class="section-title">{{ t('dashboard.recentJobs') }}</h3>
    <el-table :data="stats.jobs" style="margin-top: 8px">
      <el-table-column prop="id" :label="t('dashboard.jobId')" width="90" />
      <el-table-column prop="job_type" :label="t('common.type')" />
      <el-table-column prop="status" :label="t('common.status')" />
      <el-table-column prop="error_message" :label="t('dashboard.error')" />
    </el-table>
  </section>
</template>

<style scoped>
.dashboard-page { display: grid; gap: 14px; }
.hero h2 { margin: 0; font-size: 22px; }
.hero p { margin: 8px 0 0; color: #374151; }
.hero-flow { color: #6b7280; font-size: 13px; }
.stat-row :deep(.el-card__body) { font-weight: 600; }
.flow-card { margin-top: 4px; }
.section-title { margin: 4px 0 0; }
</style>
