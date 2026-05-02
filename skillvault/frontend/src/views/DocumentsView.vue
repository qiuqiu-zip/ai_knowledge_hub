<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'

const docs = ref<any[]>([])
const loading = ref(false)
const documentActionLoading = reactive<Record<string, boolean>>({})
const filters = reactive({
  repo: '',
  docType: '',
  language: '',
  recommended: '',
  hasSummary: '',
})
const { t } = useI18n()

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/documents')
    docs.value = data || []
  } finally {
    loading.value = false
  }
}

function shortSha(sha?: string) {
  return sha ? sha.slice(0, 7) : '-'
}

function githubUrlFromRaw(rawUrl?: string) {
  if (!rawUrl) return ''
  const prefix = 'https://raw.githubusercontent.com/'
  if (!rawUrl.startsWith(prefix)) return ''
  const rest = rawUrl.slice(prefix.length)
  const parts = rest.split('/')
  if (parts.length < 4) return ''
  const [owner, repo, branch, ...pathParts] = parts
  const path = pathParts.join('/')
  if (!owner || !repo || !branch || !path) return ''
  return `https://github.com/${owner}/${repo}/blob/${branch}/${path}`
}

function languageText(row: any) {
  const lang = row?.metadata?.language
  if (lang === 'zh') return t('languages.zh')
  if (lang === 'en') return t('languages.en')
  return t('languages.unknown')
}

function docTypeText(row: any) {
  const type = row?.metadata?.doc_type || 'other'
  return t(`docTypes.${type}`)
}

function summaryPreview(row: any) {
  const summary = row?.metadata?.summary
  if (summary) return String(summary).slice(0, 180)
  const excerpt = row?.content || ''
  if (!excerpt) return t('documents.noSummary')
  return excerpt.slice(0, 180)
}

async function copyUrl(url?: string) {
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success(t('documents.linkCopied'))
  } catch {
    ElMessage.error(t('documents.copyFailed'))
  }
}

function actionLoadingKey(documentId: number, action: string) {
  return `${documentId}:${action}`
}

async function handleDocumentAction(row: any, action: 'chunk' | 'embed' | 'summarize' | 'skill-draft') {
  const key = actionLoadingKey(row.id, action)
  if (documentActionLoading[key]) return
  documentActionLoading[key] = true
  try {
    const { data } = await api.post(`/api/documents/${row.id}/${action}`)
    ElMessage.success(t('documents.jobCreated', { id: data.job_id }))
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t('documents.createJobFailed'))
  } finally {
    documentActionLoading[key] = false
  }
}

const filteredDocs = computed(() =>
  (docs.value || []).filter((row) => {
    const repoOk = !filters.repo || String(row.repo || '').toLowerCase().includes(filters.repo.toLowerCase())
    const docTypeOk = !filters.docType || (row?.metadata?.doc_type || '') === filters.docType
    const languageOk = !filters.language || (row?.metadata?.language || 'unknown') === filters.language
    const recommendedOk =
      !filters.recommended ||
      (filters.recommended === 'yes' ? !!row?.metadata?.is_recommended : !row?.metadata?.is_recommended)
    const hasSummary = !!row?.metadata?.summary
    const summaryOk = !filters.hasSummary || (filters.hasSummary === 'yes' ? hasSummary : !hasSummary)
    return repoOk && docTypeOk && languageOk && recommendedOk && summaryOk
  }),
)

onMounted(load)
</script>

<template>
  <h2>{{ t('documents.title') }}</h2>
  <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px">
    <el-input v-model="filters.repo" :placeholder="t('documents.filterRepo')" style="width: 220px" clearable />
    <el-select v-model="filters.docType" :placeholder="t('documents.filterDocType')" clearable style="width: 140px">
      <el-option label="README" value="readme" />
      <el-option label="Guide" value="guide" />
      <el-option label="Docs" value="docs" />
      <el-option label="Skill" value="skill" />
      <el-option label="Prompt" value="prompt" />
      <el-option label="API" value="api" />
      <el-option label="Example" value="example" />
    </el-select>
    <el-select v-model="filters.language" :placeholder="t('documents.filterLanguage')" clearable style="width: 120px">
      <el-option :label="t('languages.zh')" value="zh" />
      <el-option :label="t('languages.en')" value="en" />
      <el-option :label="t('languages.unknown')" value="unknown" />
    </el-select>
    <el-select v-model="filters.recommended" :placeholder="t('documents.filterRecommended')" clearable style="width: 140px">
      <el-option :label="t('common.yes')" value="yes" />
      <el-option :label="t('common.no')" value="no" />
    </el-select>
    <el-select v-model="filters.hasSummary" :placeholder="t('documents.filterHasSummary')" clearable style="width: 120px">
      <el-option :label="t('documents.hasSummary')" value="yes" />
      <el-option :label="t('documents.noSummary')" value="no" />
    </el-select>
    <el-button @click="load">{{ t('common.refresh') }}</el-button>
  </div>

  <el-table :data="filteredDocs" v-loading="loading">
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="repo" :label="t('documents.repo')" width="180" />
    <el-table-column prop="file_path" :label="t('documents.filePath')" min-width="220" />
    <el-table-column :label="t('documents.docType')" width="120">
      <template #default="scope">{{ docTypeText(scope.row) }}</template>
    </el-table-column>
    <el-table-column :label="t('documents.lang')" width="90">
      <template #default="scope">{{ languageText(scope.row) }}</template>
    </el-table-column>
    <el-table-column :label="t('common.recommended')" width="80">
      <template #default="scope">
        <el-tag v-if="scope.row?.metadata?.is_recommended" type="success">{{ t('common.recommended') }}</el-tag>
        <span v-else>-</span>
      </template>
    </el-table-column>
    <el-table-column :label="t('documents.summaryOrExcerpt')" min-width="340">
      <template #default="scope">{{ summaryPreview(scope.row) }}</template>
    </el-table-column>
    <el-table-column :label="t('documents.commit')" width="90">
      <template #default="scope">{{ shortSha(scope.row.commit_sha) }}</template>
    </el-table-column>
    <el-table-column :label="t('documents.sourceUrl')" width="210">
      <template #default="scope">
        <el-space>
          <el-link v-if="scope.row.source_url" :href="scope.row.source_url" target="_blank" rel="noopener noreferrer">{{ t('documents.raw') }}</el-link>
          <el-link
            v-if="githubUrlFromRaw(scope.row.source_url)"
            :href="githubUrlFromRaw(scope.row.source_url)"
            target="_blank"
            rel="noopener noreferrer"
            type="success"
          >
            {{ t('documents.github') }}
          </el-link>
          <el-button text size="small" @click="copyUrl(scope.row.source_url)">{{ t('documents.copyLink') }}</el-button>
        </el-space>
      </template>
    </el-table-column>
    <el-table-column :label="t('common.actions')" width="360">
      <template #default="scope">
        <el-button size="small" :loading="documentActionLoading[`${scope.row.id}:chunk`]" @click="handleDocumentAction(scope.row, 'chunk')">{{ t('documents.chunk') }}</el-button>
        <el-button size="small" :loading="documentActionLoading[`${scope.row.id}:embed`]" @click="handleDocumentAction(scope.row, 'embed')">{{ t('documents.embed') }}</el-button>
        <el-button size="small" :loading="documentActionLoading[`${scope.row.id}:summarize`]" @click="handleDocumentAction(scope.row, 'summarize')">{{ t('documents.summarize') }}</el-button>
        <el-button
          size="small"
          type="primary"
          :loading="documentActionLoading[`${scope.row.id}:skill-draft`]"
          @click="handleDocumentAction(scope.row, 'skill-draft')"
        >
          {{ t('documents.skillDraft') }}
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
