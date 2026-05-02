import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { clearUser, getToken, logoutLocal } from '../stores/auth'
import { i18n } from '../i18n'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    if (error?.response?.status === 401) {
      logoutLocal()
      clearUser()
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.error(i18n.global.t('auth.tokenExpired'))
        await router.replace('/login')
      }
    }
    return Promise.reject(error)
  }
)

export default api
