<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const skills = ref<any[]>([])
const form = reactive({ title: '', prompt_template: '', source_type: 'manual', source_refs: [] as any[] })
const { t } = useI18n()
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)

function sourceTypeLabel(sourceType?: string) {
  const key = sourceType || 'unknown'
  const mapped = t(`sourceTypes.${key}`)
  return mapped === `sourceTypes.${key}` ? t('sourceTypes.unknown') : mapped
}

async function load() {
  const { data } = await api.get('/api/skills', { params: { page: currentPage.value, page_size: pageSize.value } })
  skills.value = Array.isArray(data) ? (data || []) : (data.items || [])
  total.value = Array.isArray(data) ? skills.value.length : Number(data.total || 0)
  if (currentPage.value > 1 && skills.value.length === 0 && total.value > 0) {
    currentPage.value -= 1
    await load()
  }
}

async function createSkill() {
  await api.post('/api/skills', { ...form, input_schema: {}, examples: [], tags: [], version: '1.0.0' })
  form.title = ''
  form.prompt_template = ''
  ElMessage.success('技能资产创建成功')
  await load()
}

async function removeSkill(id: number) {
  await api.delete(`/api/skills/${id}`)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <el-card shadow="never">
      <el-form inline>
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="Prompt 模板"><el-input v-model="form.prompt_template" /></el-form-item>
        <el-button type="primary" @click="createSkill">创建 Skill</el-button>
      </el-form>
    </el-card>

    <el-card shadow="never" style="margin-top: 12px" class="skills-panel">
      <div class="list-shell">
        <el-table :data="skills" height="100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" />
        <el-table-column label="来源类型" width="120">
          <template #default="scope">{{ sourceTypeLabel(scope.row.source_type) }}</template>
        </el-table-column>
        <el-table-column prop="source_refs" label="来源引用" />
        <el-table-column label="操作" width="120">
          <template #default="scope"><el-button size="small" type="danger" @click="removeSkill(scope.row.id)">删除</el-button></template>
        </el-table-column>
        <template #empty><el-empty description="暂无技能资产。你可以先从 Skill 草稿接受并沉淀正式技能。" /></template>
        </el-table>
      </div>
      <PaginationBar
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="total"
        @update:current-page="load"
        @update:page-size="load"
      />
    </el-card>
  </section>
</template>

<style scoped>
.skills-panel { display: flex; flex-direction: column; }
.list-shell {
  height: calc(100vh - 440px);
  max-height: calc(100vh - 390px);
  min-height: 260px;
  overflow: auto;
}
@media (max-width: 960px) {
  .list-shell {
    height: auto;
    max-height: 65vh;
    min-height: 220px;
  }
}
</style>
