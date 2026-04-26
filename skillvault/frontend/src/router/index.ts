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

const routes = [
  { path: '/', component: DashboardView },
  { path: '/sources', component: SourcesView },
  { path: '/github', component: GithubImportView },
  { path: '/documents', component: DocumentsView },
  { path: '/knowledge', component: KnowledgeView },
  { path: '/skill-candidates', component: SkillCandidatesView },
  { path: '/skills', component: SkillsView },
  { path: '/prompts', component: PromptsView },
  { path: '/search', component: SearchView },
  { path: '/jobs', component: JobsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
