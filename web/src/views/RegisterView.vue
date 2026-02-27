<template>
  <div class="register-view">
    <nav class="register-navbar">
      <div class="navbar-content">
        <router-link to="/course" class="brand-link">
          <span class="brand-text">天津大学《计算机网络》课程数智化平台</span>
        </router-link>
        <div class="nav-actions">
          <router-link to="/login" class="nav-link">已有账号？去登录</router-link>
          <router-link to="/course" class="nav-link">返回首页</router-link>
        </div>
      </div>
    </nav>

    <main class="register-main">
      <div class="register-card">
        <h1 class="register-title">用户注册</h1>
        <p class="register-desc">新用户请填写以下信息完成注册</p>

        <a-form :model="form" @finish="handleRegister" layout="vertical" class="register-form">
          <a-form-item
            label="用户名"
            name="username"
            :rules="[
              { required: true, message: '请输入用户名' },
              { min: 2, max: 20, message: '用户名长度为 2–20 个字符' },
              { pattern: /^[\u4e00-\u9fa5a-zA-Z0-9_]+$/, message: '仅支持中文、英文、数字和下划线' }
            ]"
          >
            <a-input v-model:value="form.username" placeholder="2–20 个字符" size="large" />
          </a-form-item>

          <a-form-item
            label="密码"
            name="password"
            :rules="[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少 6 位' }
            ]"
          >
            <a-input-password v-model:value="form.password" placeholder="至少 6 位" size="large" />
          </a-form-item>

          <a-form-item
            label="确认密码"
            name="confirmPassword"
            :rules="[
              { required: true, message: '请再次输入密码' },
              { validator: validateConfirm }
            ]"
          >
            <a-input-password v-model:value="form.confirmPassword" placeholder="再次输入密码" size="large" />
          </a-form-item>

          <a-form-item label="手机号（选填）" name="phone_number">
            <a-input v-model:value="form.phone_number" placeholder="可用于登录" size="large" />
          </a-form-item>

          <a-form-item v-if="errorMessage" class="form-error">
            <span class="error-text">{{ errorMessage }}</span>
          </a-form-item>

          <a-form-item>
            <a-button type="primary" html-type="submit" :loading="loading" block size="large" class="submit-btn">
              注册
            </a-button>
          </a-form-item>
        </a-form>

        <p class="login-hint">
          已有账号？
          <router-link to="/login">去登录</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  phone_number: ''
})
const loading = ref(false)
const errorMessage = ref('')

const validateConfirm = async (_rule, value) => {
  if (!value) throw new Error('请再次输入密码')
  if (value !== form.password) throw new Error('两次密码不一致')
}

const handleRegister = async () => {
  errorMessage.value = ''
  loading.value = true
  try {
    await userStore.register({
      username: form.username.trim(),
      password: form.password,
      phone_number: form.phone_number?.trim() || null
    })
    message.success('注册成功')
    const redirect = sessionStorage.getItem('redirect') || '/course'
    sessionStorage.removeItem('redirect')
    router.push(redirect)
  } catch (e) {
    errorMessage.value = e.message || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', sans-serif;
}

.register-navbar {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 24px;
}

.navbar-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand-link {
  color: #1a365d;
  font-weight: 600;
  font-size: 16px;
  text-decoration: none;
}

.brand-link:hover {
  color: #153e68;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-link {
  color: #6b7280;
  text-decoration: none;
  font-size: 14px;
}

.nav-link:hover {
  color: #1a365d;
}

.register-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  min-height: calc(100vh - 56px);
}

.register-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  padding: 32px;
}

.register-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 600;
  color: #1a365d;
}

.register-desc {
  margin: 0 0 24px 0;
  color: #6b7280;
  font-size: 14px;
}

.register-form :deep(.ant-form-item-label > label) {
  color: #4b5563;
}

.submit-btn {
  height: 44px;
  font-size: 16px;
  background: #1a365d;
  border-color: #1a365d;
}

.submit-btn:hover {
  background: #153e68 !important;
  border-color: #153e68 !important;
}

.form-error {
  margin-bottom: 0;
}

.error-text {
  color: #dc2626;
  font-size: 14px;
}

.login-hint {
  text-align: center;
  margin: 16px 0 0 0;
  color: #6b7280;
  font-size: 14px;
}

.login-hint a {
  color: #1a365d;
  font-weight: 500;
  text-decoration: none;
}

.login-hint a:hover {
  text-decoration: underline;
}
</style>
