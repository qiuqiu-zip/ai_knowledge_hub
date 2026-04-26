<script setup lang="ts">
import { ref } from 'vue'
import api from '../api/client'

const q = ref('哪些 GitHub 项目可以转成 Skill？')
const mode = ref('keyword')
const hits = ref<any[]>([])
const ragResult = ref<any>(null)

async function doSearch() {
  const { data } = await api.post('/api/search', { query: q.value, mode: mode.value, top_k: 5 })
  hits.value = data
}

async function ask() {
  const { data } = await api.post('/api/rag/ask', { question: q.value, top_k: 5 })
  ragResult.value = data
}
</script>

<template>
  <h2>Search / RAG</h2>
  <el-input v-model="q" placeholder="Ask a question" />
  <div style="margin-top: 12px">
    <el-select v-model="mode" style="width: 150px">
      <el-option value="keyword" label="keyword" />
      <el-option value="vector" label="vector" />
    </el-select>
    <el-button @click="doSearch">Search</el-button>
    <el-button type="primary" @click="ask">RAG Ask</el-button>
  </div>
  <h3>Search Hits</h3>
  <pre>{{ JSON.stringify(hits, null, 2) }}</pre>
  <h3>RAG Answer</h3>
  <pre>{{ JSON.stringify(ragResult, null, 2) }}</pre>
</template>
