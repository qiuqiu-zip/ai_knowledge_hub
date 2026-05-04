# Developer Context

## Task Objective
测试 Developer Investigation Gate。只允许修改 frontend/src/views/LoginView.vue。不要改 script，只把 .login-card border-radius 改为 18px。

## Allowed Paths
- frontend/src/views/LoginView.vue

## Forbidden Paths
- .env
- .env.*
- __pycache__/
- *.pyc
- dist/
- frontend/dist/
- node_modules/
- .idea/
- .ai-dev-supervisor/

## Target File Contents
### frontend/src/views/LoginView.vue
```text
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
        <div class="card-top">
          <div class="brand-block">
            <div class="brand-name">SkillVault</div>
            <h1 class="login-title">{{ t('auth.loginTitle') }}</h1>
            <p class="login-subtitle">Welcome back. Please sign in to continue.</p>
          </div>
          <el-select :model-value="locale" size="small" class="locale-select" @change="changeLocale">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </div>

        <el-form class="login-form" @submit.prevent="submit">
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
  padding: 24px;
  background:
    radial-gradient(1200px 450px at 10% -15%, #eef4ff 0%, transparent 60%),
    radial-gradient(900px 380px at 95% 110%, #f2f6fb 0%, transparent 55%),
    linear-gradient(180deg, #f7f9fc 0%, #f2f5f9 100%);
}

.login-shell {
  width: min(100%, 500px);
  display: grid;
  gap: 12px;
}

.privacy-tip {
  border: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.72);
  color: #6b7280;
  font-size: 12px;
  line-height: 1.45;
  padding: 8px 12px;
  border-radius: 10px;
}

.login-card {
  width: 100%;
  border-radius: 14px;
  border: 1px solid #e8edf4;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.brand-block {
  min-width: 0;
}

.brand-name {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #3b82f6;
  margin-bottom: 8px;
}

.login-title {
  margin: 0;
  font-size: 26px;
  line-height: 1.2;
  color: #111827;
  font-weight: 700;
}

.login-subtitle {
  margin: 10px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.locale-select {
  width: 132px;
  flex-shrink: 0;
}

.login-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.3;
  margin-bottom: 6px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  min-height: 44px;
  border: 1px solid #d7deea;
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: #b8c5da;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.14);
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #9ca3af;
}

.submit-btn {
  width: 100%;
  height: 46px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0.01em;
  margin-top: 4px;
}

.submit-btn:deep(.is-loading) {
  opacity: 0.9;
}

@media (max-width: 640px) {
  .login-wrap {
    padding: 16px;
  }

  .login-shell {
    width: 100%;
    max-width: 100%;
  }

  .card-top {
    flex-direction: column;
    gap: 12px;
  }

  .locale-select {
    width: 100%;
  }

  .login-title {
    font-size: 24px;
  }
}
</style>

```

## Related Context Files
- frontend/src/api/client.ts
- frontend/src/stores/auth.ts
- frontend/src/i18n/index.ts

## Git Status Summary
```text
M .ai-dev-supervisor/runs/20260502-225830/baseline_git_diff.patch
 M .ai-dev-supervisor/runs/20260502-225830/baseline_git_status.txt
 M .ai-dev-supervisor/runs/20260502-225830/dev_loop_state.json
 M frontend/src/views/LoginView.vue
?? .ai-dev-supervisor/runs/20260502-225830/iterations/
?? .ai-dev-supervisor/runs/20260503-014049/
?? .ai-dev-supervisor/runs/20260503-015806/
```

## Test Commands
- python3 -m compileall backend/app
- cd frontend && npm run build

## Safety Reminders
- Do not modify files outside allowed paths.
- Do not output secrets.
- Do not touch .env/node_modules/dist/.ai-dev-supervisor.