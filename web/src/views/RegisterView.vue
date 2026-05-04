<template>
  <div class="register-view auth-entry">
    <header class="register-header">
      <div class="register-header-content">
        <router-link to="/course" class="register-logo">
          <span class="register-logo-mark"></span>
          <span class="register-logo-text">{{ courseTitle }}</span>
        </router-link>
        <div class="register-auth">
          <router-link to="/login" class="register-auth-link">已有账号？去登录</router-link>
          <button type="button" class="register-auth-btn" @click="goHome">返回首页</button>
        </div>
      </div>
    </header>

    <main class="register-main page-shell">
      <section class="register-stage page-panel">
        <div class="register-stage-copy">
          <span class="register-stage-eyebrow">Create Account</span>
          <h1 class="register-stage-title">创建你的课程平台账号</h1>
          <p class="register-stage-subtitle">统一的学习入口，连接对话、伴读、视频与练习体验。</p>
        </div>

        <div class="register-card page-card">
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
                    pattern: /^[一-龥a-zA-Z0-9_]+$/,
                    message: '仅支持中文、英文、数字和下划线'
                  }
                ]"
              >
                <a-input v-model:value="form.username" placeholder="2–20 个字符" size="large">
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
                <a-input v-model:value="form.phone_number" placeholder="可用于登录" size="large">
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
      </section>
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
.register-view {
  min-height: 100vh;
  color: var(--text-primary);
  background:
    radial-gradient(
      circle at top left,
      color-mix(in srgb, var(--accent-primary) 12%, transparent),
      transparent 32%
    ),
    linear-gradient(180deg, var(--surface-page-alt), var(--surface-page) 24%, var(--surface-page));
}

.register-header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--surface-page) 90%, transparent);
  backdrop-filter: blur(18px);
}

.register-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 14px 28px;
}

.register-logo {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}

.register-logo-mark {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(
    135deg,
    var(--accent-primary),
    color-mix(in srgb, var(--accent-primary) 45%, #ffffff)
  );
  box-shadow: 0 0 0 6px var(--accent-soft);
}

.register-logo-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.register-auth {
  display: flex;
  align-items: center;
  gap: 10px;
}

.register-auth-link,
.register-auth-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  background: var(--surface-panel);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition:
    color var(--transition-base),
    background-color var(--transition-base),
    border-color var(--transition-base);
}

.register-auth-link:hover,
.register-auth-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.register-main {
  display: flex;
  align-items: center;
  min-height: calc(100vh - 72px);
}

.register-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 440px);
  gap: 28px;
  align-items: stretch;
  width: 100%;
  padding: 28px;
}

.register-stage-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 18px;
  padding: clamp(12px, 3vw, 28px);
}

.register-stage-eyebrow {
  display: inline-flex;
  align-self: flex-start;
  padding: 6px 10px;
  border: 1px solid color-mix(in srgb, var(--accent-primary) 18%, var(--border-subtle));
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-primary) 10%, transparent);
  color: var(--text-secondary);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.register-stage-title {
  margin: 0;
  max-width: 11ch;
  font-size: clamp(40px, 5vw, 64px);
  line-height: 0.98;
  letter-spacing: -0.05em;
  color: var(--text-primary);
}

.register-stage-subtitle {
  margin: 0;
  max-width: 560px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.7;
}

.register-card {
  display: flex;
  align-items: center;
  min-height: 100%;
  padding: 32px;
  background: color-mix(in srgb, var(--surface-elevated) 94%, transparent);
}

.form-wrapper {
  width: 100%;
}

.form-header {
  margin-bottom: 24px;
}

.welcome-text {
  margin: 0 0 6px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.form-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 22px;
  line-height: 1.4;
}

.register-form {
  :deep(.ant-form-item-label > label) {
    color: var(--text-secondary);
    font-size: 13px;
  }

  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input) {
    border-radius: 14px;
  }

  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input),
  :deep(.ant-input-password) {
    color: var(--text-primary);
    background: var(--surface-input);
    border-color: var(--border-subtle);
    box-shadow: none;
  }

  :deep(.ant-input-affix-wrapper:hover),
  :deep(.ant-input:hover),
  :deep(.ant-input-password:hover),
  :deep(.ant-input-affix-wrapper:focus-within),
  :deep(.ant-input:focus),
  :deep(.ant-input-password:focus-within) {
    border-color: var(--border-strong);
  }

  :deep(.ant-input-prefix) {
    margin-right: 10px;
    color: var(--text-muted);
  }

  :deep(.ant-btn-primary) {
    height: 46px;
    border-radius: 999px;
    border-color: color-mix(in srgb, var(--accent-primary) 28%, var(--border-subtle));
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--accent-primary) 18%, var(--surface-elevated)),
      color-mix(in srgb, var(--accent-primary) 7%, var(--surface-panel))
    );
    color: var(--text-primary);
    box-shadow: none;
  }

  :deep(.ant-btn-primary:hover) {
    border-color: color-mix(in srgb, var(--accent-primary) 52%, var(--border-strong));
    background: linear-gradient(
      180deg,
      color-mix(in srgb, var(--accent-primary) 24%, var(--surface-elevated)),
      color-mix(in srgb, var(--accent-primary) 10%, var(--surface-panel))
    );
  }
}

.submit-btn {
  font-size: 15px;
  font-weight: 600;
}

.error-message {
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, #ff6b6b 28%, var(--border-subtle));
  border-radius: 14px;
  background: color-mix(in srgb, #ff6b6b 10%, var(--surface-panel));
  color: #ffb4b4;
  font-size: 13px;
  text-align: center;
}

.login-hint {
  margin: 22px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  text-align: center;

  a {
    color: var(--text-primary);
    text-decoration: none;
  }

  a:hover {
    color: var(--accent-primary);
  }
}

@media (max-width: 1100px) {
  .register-stage {
    grid-template-columns: 1fr;
  }

  .register-stage-copy {
    padding-bottom: 0;
  }
}

@media (max-width: 640px) {
  .register-header-content {
    flex-direction: column;
    align-items: stretch;
    padding: 14px 18px;
  }

  .register-auth {
    flex-wrap: wrap;
  }

  .register-stage {
    padding: 18px;
    gap: 20px;
  }

  .register-card {
    padding: 22px 18px;
  }

  .register-logo-text {
    font-size: 14px;
    white-space: normal;
  }

  .register-stage-title {
    max-width: none;
    font-size: 34px;
  }
}
</style>
