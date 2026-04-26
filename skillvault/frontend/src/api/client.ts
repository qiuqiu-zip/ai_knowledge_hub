import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
})

const adminToken = import.meta.env.VITE_ADMIN_TOKEN
if (adminToken) {
  api.defaults.headers.common['X-Admin-Token'] = adminToken
}

export default api
