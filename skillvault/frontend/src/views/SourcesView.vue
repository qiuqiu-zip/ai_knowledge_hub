<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'

const sources = ref<any[]>([])
const form = reactive({ source_type: 'manual', name: '', url: '', owner: '', license: '', metadata: {} as Record<string, any> })
const loading = ref(false)
const creating = ref(false)
const rowLoading = reactive<Record<number, boolean>>({})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/sources')
    sources.value = data
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '加载 Sources 失败')
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
    ElMessage.error(error?.response?.data?.detail || '创建 Source 失败')
  } finally {
    creating.value = false
  }
}

function formatDate(ts?: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
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
    ElMessage.success('同步设置已更新')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '更新同步设置失败')
  } finally {
    rowLoading[row.id] = false
  }
}

async function syncNow(row: any) {
  if (row.source_type !== 'github_api') return
  rowLoading[row.id] = true
  try {
    const { data } = await api.post(`/api/sources/${row.id}/sync-now`)
    ElMessage.success(`任务已创建：job_id=${data.job_id}`)
    await load()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '触发同步失败')
  } finally {
    rowLoading[row.id] = false
  }
}

onMounted(load)
</script>

<template>
  <h2>Sources</h2>
  <el-form inline>
    <el-form-item label="Type"><el-input v-model="form.source_type" /></el-form-item>
    <el-form-item label="Name"><el-input v-model="form.name" /></el-form-item>
    <el-form-item label="URL"><el-input v-model="form.url" /></el-form-item>
    <el-button type="primary" :loading="creating" @click="createSource">Create</el-button>
  </el-form>

  <el-table :data="sources" v-loading="loading" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="source_type" label="Type" />
    <el-table-column prop="name" label="Name" />
    <el-table-column prop="url" label="URL" />
    <el-table-column prop="license" label="License" />
    <el-table-column label="Auto Sync" width="130">
      <template #default="scope">
        <el-switch
          v-model="scope.row.auto_sync_enabled"
          :disabled="scope.row.source_type !== 'github_api' || rowLoading[scope.row.id]"
          @change="updateSyncSettings(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="Interval(min)" width="150">
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
    <el-table-column label="Last Sync" width="180">
      <template #default="scope">{{ formatDate(scope.row.last_sync_at) }}</template>
    </el-table-column>
    <el-table-column label="Next Sync" width="180">
      <template #default="scope">{{ formatDate(scope.row.next_sync_at) }}</template>
    </el-table-column>
    <el-table-column label="Actions" width="140">
      <template #default="scope">
        <el-button
          size="small"
          type="primary"
          :disabled="scope.row.source_type !== 'github_api'"
          :loading="rowLoading[scope.row.id]"
          @click="syncNow(scope.row)"
        >
          Sync Now
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
