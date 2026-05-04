<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'
import PaginationBar from '../components/PaginationBar.vue'

const candidates = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)

async function load() {
  const { data } = await api.get('/api/skill-candidates', { params: { page: currentPage.value, page_size: pageSize.value } })
  candidates.value = Array.isArray(data) ? (data || []) : (data.items || [])
  total.value = Array.isArray(data) ? candidates.value.length : Number(data.total || 0)
  if (currentPage.value > 1 && candidates.value.length === 0 && total.value > 0) {
    currentPage.value -= 1
    await load()
  }
}

async function accept(id: number) {
  await api.post(`/api/skill-candidates/${id}/accept`)
  ElMessage.success('已接受并进入正式技能资产')
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <el-card shadow="never" class="candidates-panel">
      <div class="list-shell">
        <el-table :data="candidates" height="100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="草稿标题" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="license" label="许可证" />
        <el-table-column prop="source_url" label="来源链接" min-width="220" />
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button size="small" type="primary" @click="accept(scope.row.id)">接受</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无 Skill 草稿。同步内容并生成摘要后，系统会在这里沉淀可复用技能。" /></template>
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
.candidates-panel { display: flex; flex-direction: column; }
.list-shell {
  height: calc(100vh - 380px);
  max-height: calc(100vh - 340px);
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
