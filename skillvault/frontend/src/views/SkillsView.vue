<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '../api/client'

const skills = ref<any[]>([])
const form = reactive({
  title: '',
  prompt_template: '',
  source_type: 'manual',
  source_refs: [] as any[],
})

async function load() {
  const { data } = await api.get('/api/skills')
  skills.value = data
}

async function createSkill() {
  await api.post('/api/skills', {
    ...form,
    input_schema: {},
    examples: [],
    tags: [],
    version: '1.0.0',
  })
  form.title = ''
  form.prompt_template = ''
  await load()
}

async function removeSkill(id: number) {
  await api.delete(`/api/skills/${id}`)
  await load()
}

onMounted(load)
</script>

<template>
  <h2>Skills</h2>
  <el-form inline>
    <el-form-item label="Title"><el-input v-model="form.title" /></el-form-item>
    <el-form-item label="Prompt"><el-input v-model="form.prompt_template" /></el-form-item>
    <el-button type="primary" @click="createSkill">Create</el-button>
  </el-form>

  <el-table :data="skills" style="margin-top: 16px">
    <el-table-column prop="id" label="ID" width="80" />
    <el-table-column prop="title" label="Title" />
    <el-table-column prop="source_type" label="Source Type" width="120" />
    <el-table-column prop="source_refs" label="Source Refs" />
    <el-table-column label="Action" width="120">
      <template #default="scope">
        <el-button size="small" type="danger" @click="removeSkill(scope.row.id)">Delete</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
