<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'

const docs = ref<any[]>([])
const documentActionLoading = reactive<Record<string, boolean>>({})

async function load() {
  const { data } = await api.get('/api/documents')
  docs.value = data
}

function actionLoadingKey(documentId: number, action: string) {
  return `${documentId}:${action}`
}

async function handleDocumentAction(
  row: any,
  action: 'chunk' | 'embed' | 'summarize' | 'skill-draft'
) {
  const key = actionLoadingKey(row.id, action)
  if (documentActionLoading[key]) return

  documentActionLoading[key] = true
  try {
    const { data } = await api.post(`/api/documents/${row.id}/${action}`)
    ElMessage.success(`任务已创建：job_id=${data.job_id}（可到 Jobs 页面查看进度）`)
    await load()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || '请求失败'
    ElMessage.error(`创建任务失败：${detail}`)
  } finally {
    documentActionLoading[key] = false
  }
}

onMounted(load)
</script>

<template>
  <h2>Documents</h2>
  <el-button @click="load">Refresh</el-button>
  <el-table :data="docs" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="title" label="Title" />
    <el-table-column prop="source_type" label="Source Type" width="120" />
    <el-table-column prop="source_url" label="Source URL" />
    <el-table-column label="Actions" width="360">
      <template #default="scope">
        <el-button
          size="small"
          :loading="documentActionLoading[`${scope.row.id}:chunk`]"
          @click="handleDocumentAction(scope.row, 'chunk')"
        >
          Chunk
        </el-button>
        <el-button
          size="small"
          :loading="documentActionLoading[`${scope.row.id}:embed`]"
          @click="handleDocumentAction(scope.row, 'embed')"
        >
          Embed
        </el-button>
        <el-button
          size="small"
          :loading="documentActionLoading[`${scope.row.id}:summarize`]"
          @click="handleDocumentAction(scope.row, 'summarize')"
        >
          Summarize
        </el-button>
        <el-button
          size="small"
          type="primary"
          :loading="documentActionLoading[`${scope.row.id}:skill-draft`]"
          @click="handleDocumentAction(scope.row, 'skill-draft')"
        >
          Skill Draft
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
