<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    currentPage: number
    pageSize: number
    total: number
    pageSizes?: number[]
    hiddenIfEmpty?: boolean
  }>(),
  {
    pageSizes: () => [10, 20, 50, 100],
    hiddenIfEmpty: true,
  },
)

const emit = defineEmits<{
  'update:currentPage': [value: number]
  'update:pageSize': [value: number]
}>()

function onPageChange(page: number) {
  emit('update:currentPage', page)
}

function onSizeChange(size: number) {
  emit('update:pageSize', size)
  emit('update:currentPage', 1)
}
</script>

<template>
  <div v-if="!hiddenIfEmpty || total > 0" class="pagination-wrap">
    <el-pagination
      :current-page="currentPage"
      :page-size="pageSize"
      :page-sizes="pageSizes"
      :total="total"
      background
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="onPageChange"
      @size-change="onSizeChange"
    />
  </div>
</template>

<style scoped>
.pagination-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  overflow-x: auto;
}
</style>
