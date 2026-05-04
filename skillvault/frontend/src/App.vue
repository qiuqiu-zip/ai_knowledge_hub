<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser, logoutLocal } from './stores/auth'
import { useI18n } from 'vue-i18n'
import { elementLocale, getLocale, setLocale } from './i18n'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const isLoginPage = computed(() => route.path === '/login')
const { t } = useI18n()
const locale = computed({
  get: () => getLocale(),
  set: (v: string) => setLocale(v),
})

async function logout() {
  logoutLocal()
  ElMessage.success(t('common.logout'))
  await router.replace('/login')
}

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    '/': t('nav.dashboard'),
    '/sources': t('nav.sources'),
    '/github': t('nav.githubImport'),
    '/documents': t('nav.documents'),
    '/knowledge': t('nav.knowledge'),
    '/skill-candidates': t('nav.skillCandidates'),
    '/skills': t('nav.skills'),
    '/prompts': t('nav.prompts'),
    '/search': t('nav.search'),
    '/jobs': t('nav.jobs'),
    '/digests': t('nav.digests'),
  }
  return map[route.path] || t('common.appName')
})

const pageSubtitle = computed(() => {
  const map: Record<string, string> = {
    '/': t('pageSubtitle.dashboard'),
    '/sources': t('pageSubtitle.sources'),
    '/github': t('pageSubtitle.githubImport'),
    '/documents': t('pageSubtitle.documents'),
    '/knowledge': t('pageSubtitle.knowledge'),
    '/skill-candidates': t('pageSubtitle.skillCandidates'),
    '/skills': t('pageSubtitle.skills'),
    '/prompts': t('pageSubtitle.prompts'),
    '/search': t('pageSubtitle.search'),
    '/jobs': t('pageSubtitle.jobs'),
    '/digests': t('pageSubtitle.digests'),
  }
  return map[route.path] || ''
})
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <el-container v-if="!isLoginPage" class="app-shell">
      <el-aside width="248px" class="app-sidebar">
        <div class="sidebar-brand">
          <div class="brand-dot" />
          <div>
            <div class="brand-name">SkillVault</div>
            <div class="brand-sub">{{ t('common.consoleName') }}</div>
          </div>
        </div>
        <el-menu router :default-active="route.path" class="app-menu">
          <p class="menu-group">{{ t('navGroup.overview') }}</p>
          <el-menu-item index="/">{{ t('nav.dashboard') }}</el-menu-item>

          <p class="menu-group">{{ t('navGroup.ingestion') }}</p>
          <el-menu-item index="/sources">{{ t('nav.sources') }}</el-menu-item>
          <el-menu-item index="/github">{{ t('nav.githubImport') }}</el-menu-item>

          <p class="menu-group">{{ t('navGroup.content') }}</p>
          <el-menu-item index="/documents">{{ t('nav.documents') }}</el-menu-item>
          <el-menu-item index="/knowledge">{{ t('nav.knowledge') }}</el-menu-item>
          <el-menu-item index="/search">{{ t('nav.search') }}</el-menu-item>

          <p class="menu-group">{{ t('navGroup.discovery') }}</p>
          <el-menu-item index="/digests">{{ t('nav.digests') }}</el-menu-item>

          <p class="menu-group">{{ t('navGroup.assets') }}</p>
          <el-menu-item index="/skill-candidates">{{ t('nav.skillCandidates') }}</el-menu-item>
          <el-menu-item index="/skills">{{ t('nav.skills') }}</el-menu-item>
          <el-menu-item index="/prompts">{{ t('nav.prompts') }}</el-menu-item>

          <p class="menu-group">{{ t('navGroup.ops') }}</p>
          <el-menu-item index="/jobs">{{ t('nav.jobs') }}</el-menu-item>
        </el-menu>
        <div class="sidebar-footer">
          <div class="footer-hint">{{ t('common.mainSlogan') }}</div>
        </div>
      </el-aside>
      <el-main class="app-main">
        <div class="topbar">
          <div>
            <h1 class="page-title">{{ pageTitle }}</h1>
            <p class="page-subtitle">{{ pageSubtitle }}</p>
          </div>
          <div class="topbar-tools">
            <el-select v-model="locale" size="small" class="locale-switcher">
              <el-option label="中文" value="zh-CN" />
              <el-option label="English" value="en-US" />
            </el-select>
            <div class="user-chip">
              <span class="user-label">{{ t('auth.userLabel') }}</span>
              <span class="user-name">{{ currentUser?.username || '-' }}</span>
            </div>
            <el-button size="small" class="logout-btn" @click="logout">{{ t('common.logout') }}</el-button>
          </div>
        </div>
        <section class="page-body">
          <router-view />
        </section>
      </el-main>
    </el-container>
    <router-view v-else />
  </el-config-provider>
</template>

<style scoped>
.app-shell { min-height: 100vh; background: #f3f6fb; }
.app-sidebar { border-right: 1px solid #e5ebf3; background: #fbfcfe; display: flex; flex-direction: column; }
.sidebar-brand { height: 76px; display: flex; align-items: center; gap: 12px; padding: 0 18px; border-bottom: 1px solid #eef2f7; }
.brand-dot { width: 12px; height: 12px; border-radius: 999px; background: linear-gradient(145deg, #5b8cff, #3d73f5); box-shadow: 0 0 0 4px rgba(61, 115, 245, 0.12); }
.brand-name { font-size: 15px; font-weight: 700; color: #111827; }
.brand-sub { margin-top: 2px; font-size: 11px; color: #94a3b8; }
.app-menu { border-right: none; background: transparent; padding: 10px 10px 8px; flex: 1; overflow-y: auto; }
.menu-group { margin: 12px 14px 2px; font-size: 11px; color: #94a3b8; font-weight: 600; letter-spacing: .4px; }
.app-menu :deep(.el-menu-item) { height: 38px; line-height: 38px; margin: 3px 8px; border-radius: 10px; color: #475569; font-size: 14px; font-weight: 500; }
.app-menu :deep(.el-menu-item:hover) { background: #eef4ff; color: #1d4ed8; }
.app-menu :deep(.el-menu-item.is-active) { color: #1d4ed8; background: #eaf1ff; font-weight: 600; }
.sidebar-footer { border-top: 1px solid #eef2f7; padding: 12px 16px; }
.footer-hint { font-size: 12px; color: #94a3b8; line-height: 1.5; }
.app-main { padding: 18px 20px; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 2px 2px 14px; }
.page-title { margin: 0; font-size: 24px; line-height: 1.2; color: #111827; font-weight: 700; }
.page-subtitle { margin: 6px 0 0; color: #64748b; font-size: 13px; }
.topbar-tools { display: flex; align-items: center; gap: 10px; }
.locale-switcher { width: 120px; }
.user-chip { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #e2e8f0; background: #fff; border-radius: 10px; height: 32px; padding: 0 10px; }
.user-label { font-size: 12px; color: #64748b; }
.user-name { font-size: 12px; color: #0f172a; font-weight: 600; }
.logout-btn { border-radius: 10px; }
.page-body { background: #ffffff; border: 1px solid #e7edf5; border-radius: 14px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05); padding: 18px; min-height: calc(100vh - 116px); }
@media (max-width: 1100px) { .app-sidebar { width: 212px !important; } .topbar { flex-direction: column; align-items: stretch; } }
</style>
