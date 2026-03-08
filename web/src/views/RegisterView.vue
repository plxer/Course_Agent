<template>
  <div class="register-view">
    <!-- 顶部导航：与课程智能体一致 -->
    <header class="register-header">
      <div class="register-header-content">
        <router-link to="/course" class="register-logo">
          <span class="register-logo-text">{{ courseTitle }}</span>
        </router-link>
        <div class="register-auth">
          <router-link to="/login" class="register-auth-link">已有账号？去登录</router-link>
          <button type="button" class="register-auth-btn" @click="goHome">返回首页</button>
        </div>
      </div>
    </header>

    <main class="register-main">
      <div class="register-card">
        <div class="form-wrapper">
          <header class="form-header">
            <p class="welcome-text">用户注册</p>
            <h2 class="form-title">新用户请填写以下信息完成注册</h2>
          </header>

          <a-form :model="form" @finish="handleRegister" layout="vertical" class="register-form">
            <a-form-item
              label="用户名"
              name="username"
              :rules="[
                { required: true, message: '请输入用户名' },
                { min: 2, max: 20, message: '用户名长度为 2–20 个字符' },
                {
                  pattern: /^[\u4e00-\u9fa5a-zA-Z0-9_]+$/,
                  message: '仅支持中文、英文、数字和下划线'
                }
              ]"
            >
              <a-input
                v-model:value="form.username"
                placeholder="2–20 个字符"
                size="large"
              >
                <template #prefix>
                  <user-outlined />
                </template>
              </a-input>
            </a-form-item>

            <a-form-item
              label="密码"
              name="password"
              :rules="[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少 6 位' }
              ]"
            >
              <a-input-password
                v-model:value="form.password"
                placeholder="至少 6 位"
                size="large"
              >
                <template #prefix>
                  <lock-outlined />
                </template>
              </a-input-password>
            </a-form-item>

            <a-form-item
              label="确认密码"
              name="confirmPassword"
              :rules="[
                { required: true, message: '请再次输入密码' },
                { validator: validateConfirm }
              ]"
            >
              <a-input-password
                v-model:value="form.confirmPassword"
                placeholder="再次输入密码"
                size="large"
              >
                <template #prefix>
                  <lock-outlined />
                </template>
              </a-input-password>
            </a-form-item>

            <a-form-item label="手机号（选填）" name="phone_number">
              <a-input
                v-model:value="form.phone_number"
                placeholder="可用于登录"
                size="large"
              >
                <template #prefix>
                  <phone-outlined />
                </template>
              </a-input>
            </a-form-item>

            <div v-if="errorMessage" class="error-message">
              {{ errorMessage }}
            </div>

            <a-form-item>
              <a-button
                type="primary"
                html-type="submit"
                :loading="loading"
                block
                size="large"
                class="submit-btn"
              >
                注册
              </a-button>
            </a-form-item>
          </a-form>

          <p class="login-hint">
            已有账号？
            <router-link to="/login">去登录</router-link>
          </p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useInfoStore } from '@/stores/info'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, PhoneOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const infoStore = useInfoStore()

const courseTitle = '天津大学《计算机网络》课程数智化平台'

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

const goHome = () => {
  router.push('/course')
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

onMounted(() => {
  if (userStore.isLoggedIn) {
    router.push('/course')
    return
  }
  infoStore.loadInfoConfig()
})
</script>

<style lang="less" scoped>
/* 与课程智能体界面一致（ExercisesView / LoginView） */
.register-view {
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
  --primary-color: #1a365d;
  --primary-color-dark: #153e68;
  --light-bg: #f7f9fc;
  --dark-text: #2d3748;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --white: #ffffff;
  --gray-200: #e5e7eb;
  --gray-50: #f9fafb;

  min-height: 100vh;
  width: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  background-color: var(--gray-50);
  color: var(--dark-text);
}

.register-header {
  flex-shrink: 0;
  background-color: var(--white);
  border-bottom: 1px solid var(--gray-200);
}

.register-header-content {
  width: 100%;
  padding: 12px 24px 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

.register-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.register-logo-text {
  margin-left: 0;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
  font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'Roboto', sans-serif;
}

.register-auth {
  display: flex;
  align-items: center;
  gap: 12px;
}

.register-auth-link {
  color: var(--gray-500);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;
}

.register-auth-link:hover {
  color: var(--primary-color);
}

.register-auth-btn {
  font-size: 14px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  background: var(--white);
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.register-auth-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.register-main {
  flex: 1;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.register-card {
  width: 100%;
  max-width: 420px;
  background: var(--white);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  padding: 40px;
}

.form-wrapper {
  width: 100%;
}

.form-header {
  text-align: left;
  margin-bottom: 24px;

  .welcome-text {
    font-size: 14px;
    font-weight: 600;
    color: var(--gray-500);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .form-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--dark-text);
    margin: 0;
    line-height: 1.4;
  }
}

.register-form {
  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input) {
    border-radius: 8px;
  }
  :deep(.ant-btn-primary) {
    height: 44px;
    font-size: 16px;
    border-radius: 8px;
    background: var(--primary-color);
    border-color: var(--primary-color);
  }
  :deep(.ant-btn-primary:hover) {
    background: var(--primary-color-dark);
    border-color: var(--primary-color-dark);
  }
}

.submit-btn {
  height: 44px;
  font-size: 16px;
}

.error-message {
  margin-bottom: 16px;
  padding: 10px 12px;
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  color: #cf1322;
  font-size: 13px;
  text-align: center;
}

.login-hint {
  text-align: center;
  margin: 20px 0 0 0;
  color: var(--gray-500);
  font-size: 14px;

  a {
    color: var(--primary-color);
    font-weight: 500;
    text-decoration: none;
    &:hover {
      text-decoration: underline;
    }
  }
}

@media (max-width: 768px) {
  .register-header-content {
    padding: 0 20px;
  }

  .register-logo-text {
    font-size: 14px;
  }

  .register-card {
    padding: 32px 24px;
  }
}
</style>
