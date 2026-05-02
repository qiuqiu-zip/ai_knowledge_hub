import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import SourcesView from '../views/SourcesView.vue'
import GithubImportView from '../views/GithubImportView.vue'
import DocumentsView from '../views/DocumentsView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'
import SkillCandidatesView from '../views/SkillCandidatesView.vue'
import SkillsView from '../views/SkillsView.vue'
import PromptsView from '../views/PromptsView.vue'
import SearchView from '../views/SearchView.vue'
import JobsView from '../views/JobsView.vue'
import DailyDigestView from '../views/DailyDigestView.vue'
import LoginView from '../views/LoginView.vue'
import { getToken } from '../stores/auth'

const routes = [
  { path: '/login', component: LoginView, meta: { requiresAuth: false } },
  { path: '/', component: DashboardView, meta: { requiresAuth: true } },
  { path: '/sources', component: SourcesView, meta: { requiresAuth: true } },
  { path: '/github', component: GithubImportView, meta: { requiresAuth: true } },
  { path: '/documents', component: DocumentsView, meta: { requiresAuth: true } },
  { path: '/knowledge', component: KnowledgeView, meta: { requiresAuth: true } },
  { path: '/skill-candidates', component: SkillCandidatesView, meta: { requiresAuth: true } },
  { path: '/skills', component: SkillsView, meta: { requiresAuth: true } },
  { path: '/prompts', component: PromptsView, meta: { requiresAuth: true } },
  { path: '/search', component: SearchView, meta: { requiresAuth: true } },
  { path: '/jobs', component: JobsView, meta: { requiresAuth: true } },
  { path: '/digests', component: DailyDigestView, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = getToken()
  if (to.path === '/login' && token) {
    return '/'
  }
  if (to.meta.requiresAuth && !token) {
    return '/login'
  }
  return true
})

export default router
