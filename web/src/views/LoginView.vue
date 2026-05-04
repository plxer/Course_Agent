<template>
  <div class="login-view" :class="{ 'has-alert': serverStatus === 'error' }">
    <div v-if="serverStatus === 'error'" class="server-status-alert page-card">
      <div class="alert-content">
        <exclamation-circle-outlined class="alert-icon" />
        <div class="alert-text">
          <div class="alert-title">服务端连接失败</div>
          <div class="alert-message">{{ serverError }}</div>
        </div>
        <a-button type="link" size="small" @click="checkServerHealth" :loading="healthChecking">
          重试
        </a-button>
      </div>
    </div>

    <header class="login-header">
      <div class="login-header-content">
        <router-link to="/course" class="login-logo">
          <span class="login-logo-mark"></span>
          <span class="login-logo-text">{{ courseTitle }}</span>
        </router-link>
        <div class="login-auth">
          <router-link to="/guide" class="login-auth-link">使用指南</router-link>
          <router-link to="/register" class="login-auth-link primary">注册</router-link>
          <button type="button" class="login-auth-btn" @click="goHome">返回首页</button>
        </div>
      </div>
    </header>

    <main class="login-main">
      <section class="login-visual">
        <img :src="loginBgImage" alt="登录背景" class="login-bg-image" />
        <div class="login-visual-copy">
          <h1>天津大学课程数智化平台</h1>
          <p>{{ brandSubtitle }}</p>
        </div>
      </section>

      <section class="login-form-panel">
            <div class="form-wrapper">
              <header class="form-header">
                <p class="welcome-text">欢迎登录</p>
                <h2 v-if="isFirstRun" class="init-title">系统初始化，请创建超级管理员</h2>
                <h2 v-else class="init-title">使用账号继续访问平台</h2>
              </header>

              <div class="login-content" :class="{ 'is-initializing': isFirstRun }">
                <div v-if="isFirstRun" class="login-form login-form--init">
                  <a-form :model="adminForm" @finish="handleInitialize" layout="vertical">
                    <a-form-item
                      label="用户ID"
                      name="user_id"
                      :rules="[
                        { required: true, message: '请输入用户ID' },
                        {
                          pattern: /^[a-zA-Z0-9_]+$/,
                          message: '用户ID只能包含字母、数字和下划线'
                        },
                        {
                          min: 3,
                          max: 20,
                          message: '用户ID长度必须在3-20个字符之间'
                        }
                      ]"
                    >
                      <a-input
                        v-model:value="adminForm.user_id"
                        placeholder="请输入用户ID（3-20个字符）"
                        :maxlength="20"
                      />
                    </a-form-item>

                    <a-form-item
                      label="手机号（可选）"
                      name="phone_number"
                      :rules="[
                        {
                          validator: async (_rule, value) => {
                            if (!value || value.trim() === '') {
                              return
                            }
                            const phoneRegex = /^1[3-9]\d{9}$/
                            if (!phoneRegex.test(value)) {
                              throw new Error('请输入正确的手机号格式')
                            }
                          }
                        }
                      ]"
                    >
                      <a-input
                        v-model:value="adminForm.phone_number"
                        placeholder="可用于登录，可不填写"
                        :maxlength="11"
                      />
                    </a-form-item>

                    <a-form-item
                      label="密码"
                      name="password"
                      :rules="[{ required: true, message: '请输入密码' }]"
                    >
                      <a-input-password v-model:value="adminForm.password" />
                    </a-form-item>

                    <a-form-item
                      label="确认密码"
                      name="confirmPassword"
                      :rules="[
                        { required: true, message: '请确认密码' },
                        { validator: validateConfirmPassword }
                      ]"
                    >
                      <a-input-password v-model:value="adminForm.confirmPassword" />
                    </a-form-item>

                    <a-form-item>
                      <a-button
                        type="primary"
                        html-type="submit"
                        :loading="loading"
                        block
                        size="large"
                      >
                        创建管理员账户
                      </a-button>
                    </a-form-item>
                  </a-form>
                </div>

                <div v-else class="login-form">
                  <a-form :model="loginForm" @finish="handleLogin" layout="vertical">
                    <a-form-item
                      label="登录账号"
                      name="loginId"
                      :rules="[{ required: true, message: '请输入用户ID、用户名或手机号' }]"
                    >
                      <a-input
                        v-model:value="loginForm.loginId"
                        placeholder="用户ID、用户名或手机号"
                      >
                        <template #prefix>
                          <user-outlined />
                        </template>
                      </a-input>
                    </a-form-item>

                    <a-form-item
                      label="密码"
                      name="password"
                      :rules="[{ required: true, message: '请输入密码' }]"
                    >
                      <a-input-password v-model:value="loginForm.password">
                        <template #prefix>
                          <lock-outlined />
                        </template>
                      </a-input-password>
                    </a-form-item>

                    <a-form-item>
                      <div class="login-options">
                        <a-checkbox v-model:checked="rememberMe">记住我</a-checkbox>
                        <a class="forgot-password" href="javascript:void(0)">忘记密码?</a>
                      </div>
                    </a-form-item>

                    <a-form-item>
                      <a-button
                        type="primary"
                        html-type="submit"
                        :loading="loading"
                        :disabled="isLocked"
                        block
                        size="large"
                      >
                        <span v-if="isLocked">账户已锁定 {{ formatTime(lockRemainingTime) }}</span>
                        <span v-else>登录</span>
                      </a-button>
                    </a-form-item>

                    <p class="register-hint">
                      没有账号？
                      <router-link to="/register">去注册</router-link>
                    </p>
                  </a-form>
                </div>

                <div v-if="errorMessage" class="error-message">
                  {{ errorMessage }}
                </div>
              </div>
            </div>
        </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useInfoStore } from '@/stores/info'
import { message } from 'ant-design-vue'
import { healthApi } from '@/apis/system_api'
import { UserOutlined, LockOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
const router = useRouter()
const userStore = useUserStore()
const infoStore = useInfoStore()

// 品牌展示数据
const loginBgImage = computed(() => {
  return infoStore.organization?.login_bg || '/login-bg.jpg'
})
const brandOrgName = computed(() => {
  return infoStore.organization?.name?.trim() || ''
})
const brandName = computed(() => {
  const orgName = brandOrgName.value
  const brandNameRaw = infoStore.branding?.name?.trim() || '课程智能体平台'

  if (orgName && brandNameRaw && orgName !== brandNameRaw) {
    return brandNameRaw
  }

  return orgName || brandNameRaw
})
const brandSubtitle = computed(() => {
  const rawSubtitle = infoStore.branding?.subtitle ?? ''
  const trimmed = rawSubtitle.trim()
  return trimmed || '面向课程学习的智能问答与伴读系统'
})
// 顶栏固定标题，与课程页一致
const courseTitle = '天津大学《计算机网络》课程数智化平台'

// 状态
const isFirstRun = ref(false)
const loading = ref(false)
const errorMessage = ref('')
// 恢复上次登录时的「记住我」勾选状态
const rememberMe = ref(localStorage.getItem('remember_me') === '1')
const serverStatus = ref('loading')
const serverError = ref('')
const healthChecking = ref(false)

// 登录锁定相关状态
const isLocked = ref(false)
const lockRemainingTime = ref(0)
const lockCountdown = ref(null)

// 登录表单
const loginForm = reactive({
  loginId: '', // 支持user_id或phone_number登录
  password: ''
})

// 管理员初始化表单
const adminForm = reactive({
  user_id: '', // 改为直接输入user_id
  password: '',
  confirmPassword: '',
  phone_number: '' // 手机号字段（可选）
})

const goHome = () => {
  router.push('/')
}

// 清理倒计时器
const clearLockCountdown = () => {
  if (lockCountdown.value) {
    clearInterval(lockCountdown.value)
    lockCountdown.value = null
  }
}

// 启动锁定倒计时
const startLockCountdown = (remainingSeconds) => {
  clearLockCountdown()
  isLocked.value = true
  lockRemainingTime.value = remainingSeconds

  lockCountdown.value = setInterval(() => {
    lockRemainingTime.value--
    if (lockRemainingTime.value <= 0) {
      clearLockCountdown()
      isLocked.value = false
      errorMessage.value = ''
    }
  }, 1000)
}

// 格式化时间显示
const formatTime = (seconds) => {
  if (seconds < 60) {
    return `${seconds}秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}分${remainingSeconds}秒`
  } else if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分钟`
  } else {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    return `${days}天${hours}小时`
  }
}

// 密码确认验证
const validateConfirmPassword = async (rule, value) => {
  if (value === '') {
    throw new Error('请确认密码')
  }
  if (value !== adminForm.password) {
    throw new Error('两次输入的密码不一致')
  }
}

// 处理登录
const handleLogin = async () => {
  // 如果当前被锁定，不允许登录
  if (isLocked.value) {
    message.warning(`账户被锁定，请等待 ${formatTime(lockRemainingTime.value)}`)
    return
  }

  try {
    loading.value = true
    errorMessage.value = ''
    clearLockCountdown()

    await userStore.login({
      loginId: loginForm.loginId,
      password: loginForm.password,
      rememberMe: rememberMe.value
    })

    localStorage.setItem('remember_me', rememberMe.value ? '1' : '0')
    message.success('登录成功')

    // 登录后统一跳转课程智能体；若有保存的访问路径则优先跳转该路径
    const redirectPath = sessionStorage.getItem('redirect') || '/course'
    sessionStorage.removeItem('redirect')
    router.push(redirectPath)
  } catch (error) {
    console.error('登录失败:', error)

    // 检查是否是锁定错误（HTTP 423）
    if (error.status === 423) {
      // 尝试从响应头中获取剩余时间
      let remainingTime = 0
      if (error.headers && error.headers.get) {
        const lockRemainingHeader = error.headers.get('X-Lock-Remaining')
        if (lockRemainingHeader) {
          remainingTime = parseInt(lockRemainingHeader)
        }
      }

      // 如果没有从头中获取到，尝试从错误消息中解析
      if (remainingTime === 0) {
        const lockTimeMatch = error.message.match(/(\d+)\s*秒/)
        if (lockTimeMatch) {
          remainingTime = parseInt(lockTimeMatch[1])
        }
      }

      if (remainingTime > 0) {
        startLockCountdown(remainingTime)
        errorMessage.value = `由于多次登录失败，账户已被锁定 ${formatTime(remainingTime)}`
      } else {
        errorMessage.value = error.message || '账户被锁定，请稍后再试'
      }
    } else {
      errorMessage.value = error.message || '登录失败，请检查用户名和密码'
    }
  } finally {
    loading.value = false
  }
}

// 处理初始化管理员
const handleInitialize = async () => {
  try {
    loading.value = true
    errorMessage.value = ''

    if (adminForm.password !== adminForm.confirmPassword) {
      errorMessage.value = '两次输入的密码不一致'
      return
    }

    await userStore.initialize({
      user_id: adminForm.user_id,
      password: adminForm.password,
      phone_number: adminForm.phone_number || null // 空字符串转为null
    })

    message.success('管理员账户创建成功')
    router.push('/course')
  } catch (error) {
    console.error('初始化失败:', error)
    errorMessage.value = error.message || '初始化失败，请重试'
  } finally {
    loading.value = false
  }
}

// 检查是否是首次运行
const checkFirstRunStatus = async () => {
  try {
    loading.value = true
    const isFirst = await userStore.checkFirstRun()
    isFirstRun.value = isFirst
  } catch (error) {
    console.error('检查首次运行状态失败:', error)
    errorMessage.value = '系统出错，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 检查服务器健康状态
const checkServerHealth = async () => {
  try {
    healthChecking.value = true
    const response = await healthApi.checkHealth()
    if (response.status === 'ok') {
      serverStatus.value = 'ok'
    } else {
      serverStatus.value = 'error'
      serverError.value = response.message || '服务端状态异常'
    }
  } catch (error) {
    console.error('检查服务器健康状态失败:', error)
    serverStatus.value = 'error'
    serverError.value = error.message || '无法连接到服务端，请检查网络连接'
  } finally {
    healthChecking.value = false
  }
}

// 组件挂载时
onMounted(async () => {
  await infoStore.loadInfoConfig()

  // 如果已登录，直接进入课程智能体
  if (userStore.isLoggedIn) {
    router.push('/course')
    return
  }

  // 首先检查服务器健康状态
  await checkServerHealth()

  // 检查是否是首次运行
  await checkFirstRunStatus()
})

// 组件卸载时清理定时器
onUnmounted(() => {
  clearLockCountdown()
})
</script>

<style lang="less" scoped>
.login-view {
  position: relative;
  min-height: 100vh;
  color: var(--text-primary);
  background:
    radial-gradient(
      circle at top left,
      color-mix(in srgb, var(--accent-primary) 7%, transparent),
      transparent 34%
    ),
    linear-gradient(180deg, var(--surface-page-alt), var(--surface-page) 22%, var(--surface-page));

  &.has-alert {
    padding-top: 76px;
  }
}

.login-header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--surface-page) 90%, transparent);
  backdrop-filter: blur(18px);
}

.login-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: min(100%, 1440px);
  margin: 0 auto;
  padding: 14px 28px;
}

.login-logo {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}

.login-logo-mark {
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

.login-logo-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.login-auth {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.login-auth-link,
.login-auth-btn {
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
  transition:
    color var(--transition-base),
    background-color var(--transition-base),
    border-color var(--transition-base);
}

.login-auth-link:hover,
.login-auth-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.login-auth-link.primary {
  border-color: color-mix(in srgb, var(--accent-primary) 28%, var(--border-subtle));
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--accent-primary) 18%, var(--surface-elevated)),
    color-mix(in srgb, var(--accent-primary) 7%, var(--surface-panel))
  );
  color: var(--text-primary);
}

.login-auth-link.primary:hover {
  border-color: color-mix(in srgb, var(--accent-primary) 52%, var(--border-strong));
}

.login-main {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(28px, 4vw, 56px);
  min-height: calc(100vh - 65px);
  padding: clamp(32px, 5vw, 72px);
}

.login-visual {
  position: relative;
  width: min(34vw, 420px);
  min-width: 340px;
  height: min(620px, calc(100vh - 160px));
  min-height: 520px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 28px;
  background: var(--surface-page-alt);
  box-shadow: 0 18px 48px var(--shadow-0);
}

.login-bg-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.login-visual::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.34));
}

.login-visual-copy {
  position: absolute;
  left: clamp(24px, 3vw, 40px);
  right: clamp(24px, 3vw, 40px);
  bottom: clamp(32px, 6vh, 64px);
  z-index: 1;
  color: #ffffff;
}

.login-visual-copy h1 {
  margin: 0;
  font-size: clamp(24px, 2.1vw, 32px);
  line-height: 1.24;
  font-weight: 560;
  letter-spacing: 0.02em;
  white-space: normal;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.28);
}

.login-visual-copy p {
  margin: 12px 0 0;
  max-width: 100%;
  color: rgba(255, 255, 255, 0.86);
  font-size: 15px;
  line-height: 1.68;
}

.login-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  width: min(100%, 520px);
  min-height: auto;
  padding: clamp(36px, 5vw, 64px);
  border: 1px solid var(--border-subtle);
  border-radius: 28px;
  background: var(--surface-panel-2);
  box-shadow: 0 18px 48px var(--shadow-0);
}

.form-wrapper {
  width: min(100%, 440px);
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

.init-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 22px;
  line-height: 1.4;
}

.login-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login-form {
  :deep(.ant-form-item-label > label) {
    color: var(--text-secondary);
    font-size: 13px;
  }

  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input),
  :deep(.ant-input-password) {
    color: var(--text-primary);
    background: var(--surface-input);
    border-color: var(--border-subtle);
    border-radius: 14px;
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

  :deep(.ant-checkbox-wrapper) {
    color: var(--text-secondary);
  }

  :deep(.ant-btn-primary) {
    height: 46px;
    border-radius: 999px;
    border-color: var(--accent-primary);
    background: var(--accent-primary);
    color: #ffffff;
    box-shadow: none;
  }

  :deep(.ant-btn-primary:hover) {
    border-color: var(--accent-primary-hover);
    background: var(--accent-primary-hover);
  }
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

.forgot-password {
  color: var(--text-secondary);
  text-decoration: none;
}

.forgot-password:hover {
  color: var(--accent-primary);
}

.register-hint {
  margin: 8px 0 0;
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

.error-message {
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, #ff6b6b 28%, var(--border-subtle));
  border-radius: 14px;
  background: color-mix(in srgb, #ff6b6b 10%, var(--surface-panel));
  color: #ffb4b4;
  font-size: 13px;
  text-align: center;
}

.server-status-alert {
  position: absolute;
  top: 12px;
  left: 50%;
  z-index: 20;
  width: min(calc(100% - 32px), 1120px);
  padding: 12px 16px;
  border: 1px solid color-mix(in srgb, #ff6b6b 36%, var(--border-subtle));
  background: color-mix(in srgb, #a82020 60%, var(--surface-panel));
  color: #fff2f2;
  transform: translateX(-50%);
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-icon {
  flex-shrink: 0;
  font-size: 18px;
}

.alert-text {
  flex: 1;
  min-width: 0;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
}

.alert-message {
  margin-top: 2px;
  font-size: 13px;
  opacity: 0.92;
}

.server-status-alert :deep(.ant-btn-link) {
  color: #fff;
}

.server-status-alert :deep(.ant-btn-link:hover) {
  color: #fff;
}

@media (max-width: 980px) {
  .login-main {
    flex-direction: column;
    align-items: stretch;
    padding: 24px 22px 56px;
  }

  .login-visual {
    width: 100%;
    min-width: 0;
    height: 34vh;
    min-height: 260px;
  }

  .login-form-panel {
    width: 100%;
    min-height: auto;
    padding: 36px 22px 56px;
  }

  .login-visual-copy h1 {
    white-space: normal;
  }
}

@media (max-width: 760px) {
  .login-header-content {
    flex-direction: column;
    align-items: stretch;
    padding: 14px 18px;
  }

  .form-wrapper {
    width: 100%;
  }

  .login-logo-text {
    font-size: 14px;
    white-space: normal;
  }

  .login-options {
    flex-direction: column;
    align-items: flex-start;
  }

  .server-status-alert {
    top: 10px;
    width: calc(100% - 20px);
  }

  .alert-content {
    align-items: flex-start;
  }
}
</style>
