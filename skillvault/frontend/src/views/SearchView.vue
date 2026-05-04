<script setup lang="ts">
import { ref } from 'vue'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const q = ref('哪些 GitHub 项目可以转成 Skill？')
const mode = ref('keyword')
const hits = ref<any[]>([])
const ragResult = ref<any>(null)
const currentPage = ref(1)
const pageSize = ref(5)

async function doSearch() {
  const { data } = await api.post('/api/search', { query: q.value, mode: mode.value, top_k: 5 })
  hits.value = data
  currentPage.value = 1
}

async function ask() {
  const { data } = await api.post('/api/rag/ask', { question: q.value, top_k: 5 })
  ragResult.value = data
}

const pagedHits = () => {
  const start = (currentPage.value - 1) * pageSize.value
  return (hits.value || []).slice(start, start + pageSize.value)
}
</script>

<template>
  <section class="search-page">
    <el-card shadow="never">
      <el-input v-model="q" placeholder="输入问题，例如：哪些项目适合生成 Skill？" />
      <div style="margin-top: 12px; display:flex; gap:8px; align-items:center; flex-wrap: wrap;">
        <el-select v-model="mode" style="width: 160px">
          <el-option value="keyword" label="关键词检索" />
          <el-option value="vector" label="向量检索" />
        </el-select>
        <el-button @click="doSearch">检索</el-button>
        <el-button type="primary" @click="ask">知识问答</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="results-panel">
      <template #header>检索结果</template>
      <div class="list-shell">
        <pre>{{ JSON.stringify(pagedHits(), null, 2) }}</pre>
      </div>
      <PaginationBar
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="(hits || []).length"
        @update:current-page="() => {}"
        @update:page-size="() => {}"
      />
    </el-card>

    <el-card shadow="never">
      <template #header>问答结果</template>
      <pre>{{ JSON.stringify(ragResult, null, 2) }}</pre>
    </el-card>
  </section>
</template>

<style scoped>
.search-page { display: grid; gap: 12px; }
.results-panel { display: flex; flex-direction: column; }
.list-shell {
  height: calc(100vh - 470px);
  max-height: calc(100vh - 410px);
  min-height: 220px;
  overflow: auto;
}
@media (max-width: 960px) {
  .list-shell {
    height: auto;
    max-height: 60vh;
    min-height: 180px;
  }
}
</style>
