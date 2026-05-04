<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api/client'
import { setToken, setUser } from '../stores/auth'
import { getLocale, setLocale } from '../i18n'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const locale = ref(getLocale())
const form = reactive({
  username: '',
  password: '',
})

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning(t('auth.pleaseInput'))
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/api/auth/login', {
      username: form.username.trim(),
      password: form.password,
    })
    setToken(data.access_token)
    setUser(data.user)
    ElMessage.success(t('auth.loginSuccess'))
    await router.replace('/')
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || t('auth.loginFailed'))
  } finally {
    loading.value = false
  }
}

function changeLocale(v: string) {
  setLocale(v)
  locale.value = getLocale()
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-shell">
      <div class="privacy-tip">
        <span>若此页面未按预期显示，可降低浏览器高级隐私保护后重试。</span>
      </div>

      <el-card class="login-card" shadow="never">
        <div class="card-header">
          <div class="brand-row">
            <div class="brand-name">SkillVault</div>
            <el-select :model-value="locale" size="small" class="locale-select" @change="changeLocale">
              <el-option label="中文" value="zh-CN" />
              <el-option label="English" value="en-US" />
            </el-select>
          </div>
          <div class="title-block">
            <h1 class="login-title">{{ t('auth.loginTitle') }}</h1>
            <p class="login-subtitle">Welcome back. Please sign in to continue.</p>
          </div>
        </div>

        <el-form class="login-form" label-position="top" @submit.prevent="submit">
          <el-form-item :label="t('auth.username')">
            <el-input v-model="form.username" autocomplete="username" />
          </el-form-item>
          <el-form-item :label="t('auth.password')">
            <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
          </el-form-item>
          <el-button class="submit-btn" type="primary" :loading="loading" @click="submit">{{ t('auth.loginButton') }}</el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background:
    radial-gradient(1200px 450px at 10% -15%, #eef4ff 0%, transparent 60%),
    radial-gradient(900px 380px at 95% 110%, #f2f6fb 0%, transparent 55%),
    linear-gradient(180deg, #f7f9fc 0%, #f2f5f9 100%);
}

.login-shell {
  width: min(100%, 420px);
  display: grid;
  gap: 10px;
}

.privacy-tip {
  border: 1px solid #e7edf6;
  background: rgba(255, 255, 255, 0.7);
  color: #6b7280;
  font-size: 11px;
  line-height: 1.35;
  padding: 6px 10px;
  border-radius: 8px;
}

.login-card {
  width: 100%;
  border-radius: 14px;
  border: 1px solid #e8edf4;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
  padding: 32px;
}

.card-header {
  display: grid;
  gap: 14px;
  margin-bottom: 20px;
}

.brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.brand-name {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #3b82f6;
}

.title-block {
  min-width: 0;
}

.login-title {
  margin: 0;
  font-size: 24px;
  line-height: 1.2;
  color: #111827;
  font-weight: 700;
}

.login-subtitle {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.login-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.3;
  margin-bottom: 6px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  min-height: 42px;
  border: 1px solid #d7deea;
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: #b8c5da;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #9ca3af;
}

.submit-btn {
  width: 100%;
  height: 43px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.01em;
  margin-top: 2px;
}

.submit-btn:deep(.is-loading) {
  opacity: 0.9;
}

.locale-select {
  width: 108px;
  flex-shrink: 0;
}

.locale-select :deep(.el-input__wrapper) {
  min-height: 34px;
  border-radius: 8px;
}

@media (max-width: 640px) {
  .login-wrap {
    padding: 16px;
  }

  .login-shell {
    width: 100%;
    max-width: 100%;
  }

  .login-card {
    padding: 24px 18px;
  }

  .card-header {
    margin-bottom: 18px;
  }

  .login-title {
    font-size: 22px;
  }
}
</style>
