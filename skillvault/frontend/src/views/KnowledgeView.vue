<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'

const list = ref<any[]>([])

async function load() {
  const { data } = await api.get('/api/knowledge')
  list.value = data
}

onMounted(load)
</script>

<template>
  <h2>Knowledge</h2>
  <el-table :data="list">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="title" label="Title" />
    <el-table-column prop="summary" label="Summary" />
    <el-table-column prop="tags" label="Tags" />
  </el-table>
</template>
