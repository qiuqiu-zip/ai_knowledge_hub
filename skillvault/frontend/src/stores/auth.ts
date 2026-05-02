import { ref } from 'vue'

const TOKEN_KEY = 'skillvault_token'
const USER_KEY = 'skillvault_user'

export const currentUser = ref<any | null>(null)

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function setUser(user: any) {
  currentUser.value = user
  localStorage.setItem(USER_KEY, JSON.stringify(user || null))
}

export function loadUserFromStorage() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) {
    currentUser.value = null
    return
  }
  try {
    currentUser.value = JSON.parse(raw)
  } catch {
    currentUser.value = null
  }
}

export function clearUser() {
  currentUser.value = null
  localStorage.removeItem(USER_KEY)
}

export function logoutLocal() {
  clearToken()
  clearUser()
}
