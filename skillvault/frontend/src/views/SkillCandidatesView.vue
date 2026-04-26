<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'

const candidates = ref<any[]>([])

async function load() {
  const { data } = await api.get('/api/skill-candidates')
  candidates.value = data
}

async function accept(id: number) {
  await api.post(`/api/skill-candidates/${id}/accept`)
  await load()
}

onMounted(load)
</script>

<template>
  <h2>Skill Candidates</h2>
  <el-table :data="candidates">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="title" label="Title" />
    <el-table-column prop="status" label="Status" width="120" />
    <el-table-column prop="license" label="License" />
    <el-table-column prop="source_url" label="Source URL" />
    <el-table-column label="Action" width="120">
      <template #default="scope">
        <el-button size="small" type="primary" @click="accept(scope.row.id)">Accept</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
