<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'github-markdown-css/github-markdown.css'
import 'highlight.js/styles/github.css'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    content?: string
  }>(),
  {
    content: '',
  },
)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class=\"hljs\"><code>${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`
      } catch {
        return `<pre class=\"hljs\"><code>${md.utils.escapeHtml(str)}</code></pre>`
      }
    }
    return `<pre class=\"hljs\"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

const defaultRender = md.renderer.rules.link_open
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  if (defaultRender) {
    return defaultRender(tokens, idx, options, env, self)
  }
  return self.renderToken(tokens, idx, options)
}

const renderedHtml = computed(() => {
  const text = props.content?.trim() || ''
  if (!text) return ''
  return md.render(text)
})
</script>

<template>
  <div class="markdown-preview-wrap">
    <el-empty v-if="!renderedHtml" description="暂无内容" />
    <div v-else class="markdown-body markdown-preview-content" v-html="renderedHtml" />
  </div>
</template>

<style scoped>
.markdown-preview-wrap {
  width: 100%;
}

.markdown-preview-content {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 20px;
  line-height: 1.8;
  color: #1f2937;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.markdown-preview-content :deep(pre) {
  overflow-x: auto;
  border-radius: 8px;
}

.markdown-preview-content :deep(code) {
  word-break: break-word;
}

.markdown-preview-content :deep(table) {
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-preview-content :deep(th),
.markdown-preview-content :deep(td) {
  border: 1px solid #d1d5db;
  padding: 8px 10px;
}

.markdown-preview-content :deep(a) {
  word-break: break-all;
}
</style>
