import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import api from './api/client'
import { getToken, loadUserFromStorage, logoutLocal, setUser } from './stores/auth'
import { i18n } from './i18n'

async function bootstrap() {
  loadUserFromStorage()
  const token = getToken()
  if (token && router.currentRoute.value.path !== '/login') {
    try {
      const { data } = await api.get('/api/auth/me')
      setUser(data)
    } catch {
      logoutLocal()
      await router.replace('/login')
    }
  }
  createApp(App).use(router).use(i18n).use(ElementPlus).mount('#app')
}

bootstrap()
