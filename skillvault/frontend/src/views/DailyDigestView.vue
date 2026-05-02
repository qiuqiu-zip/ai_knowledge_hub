<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import MarkdownPreview from '../components/MarkdownPreview.vue'

const digests = ref<any[]>([])
const activeDigest = ref<any | null>(null)
const loading = ref(false)
const detailVisible = ref(false)
const generateLoading = ref(false)
const { t } = useI18n()

function formatDate(ts?: string) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/digests')
    digests.value = data || []
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || t('digest.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function generateTodayDigest() {
  generateLoading.value = true
  try {
    const { data } = await api.post('/api/digests/generate', {})
    if (data?.created) {
      ElMessage.success(`已创建简报任务：job_id=${data.job_id}`)
    } else {
      ElMessage.info(data?.reason || '今日简报任务已存在')
    }
    await load()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '生成简报任务失败')
  } finally {
    generateLoading.value = false
  }
}

function openDetail(row: any) {
  activeDigest.value = row
  detailVisible.value = true
}

async function copyDigest() {
  if (!activeDigest.value?.content) return
  try {
    await navigator.clipboard.writeText(activeDigest.value.content)
    ElMessage.success(t('digest.copied'))
  } catch (error) {
    console.error(error)
    ElMessage.error(t('documents.copyFailed'))
  }
}

const statsEntries = computed(() => {
  const stats = activeDigest.value?.stats_json || {}
  return Object.entries(stats)
})

onMounted(load)
</script>

<template>
  <section class="digest-page">
    <div class="digest-toolbar">
      <div>
        <h2 class="digest-title">{{ t('digest.title') }}</h2>
        <p class="digest-subtitle">Track synchronization highlights and knowledge recommendations</p>
      </div>
      <div class="digest-toolbar-actions">
        <el-button :loading="generateLoading" type="primary" plain @click="generateTodayDigest">生成今日简报</el-button>
        <el-button @click="load">{{ t('common.refresh') }}</el-button>
      </div>
    </div>

    <el-card class="digest-table-card" shadow="never">
      <el-table :data="digests" v-loading="loading" class="digest-table">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="digest_date" :label="t('digest.date')" width="130" />
        <el-table-column prop="title" :label="t('common.summary')" min-width="300" />
        <el-table-column :label="t('digest.createdAt')" width="180">
          <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="120">
          <template #default="scope">
            <el-button size="small" type="primary" @click="openDetail(scope.row)">{{ t('common.view') }}</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无每日简报">
            <p class="digest-empty-tip">
              可能原因：定时任务尚未运行、今日未到生成时间、worker 未消费任务，或当前没有可统计数据。
            </p>
          </el-empty>
        </template>
      </el-table>
    </el-card>
  </section>

  <el-dialog v-model="detailVisible" :title="activeDigest?.title || t('digest.title')" width="1000px" top="4vh">
    <div style="max-height: 80vh; overflow-y: auto; display: grid; gap: 16px">
      <el-descriptions :title="t('digest.stats')" :column="2" border size="small">
        <el-descriptions-item v-for="[k, v] in statsEntries" :key="String(k)" :label="String(k)">
          {{ typeof v === 'object' ? JSON.stringify(v) : v }}
        </el-descriptions-item>
      </el-descriptions>
      <MarkdownPreview :content="activeDigest?.content || ''" />
    </div>
    <template #footer>
      <el-button @click="copyDigest">{{ t('digest.copyDigest') }}</el-button>
      <el-button @click="detailVisible = false">{{ t('common.close') }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.digest-page {
  display: grid;
  gap: 14px;
}

.digest-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.digest-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.digest-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.digest-subtitle {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.digest-table-card {
  border: 1px solid #e7edf5;
  border-radius: 12px;
}

.digest-table :deep(.el-table__header th) {
  background: #f8fafc;
  color: #334155;
  font-weight: 600;
}

.digest-empty-tip {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
  max-width: 560px;
}
</style>
