<script setup lang="ts">
import { onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { ApiError } from '@/api/http'
import { resetPassword, sendResetCode } from '@/api/user'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const sending = ref(false)
const countdown = ref(0)
const form = reactive({
  email: '',
  verificationCode: '',
  newPassword: '',
  confirmPassword: '',
})

let timer = 0

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  verificationCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位', trigger: 'blur' },
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码为 8 到 128 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.newPassword) callback(new Error('两次密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

function startCountdown() {
  countdown.value = 60
  timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(timer)
  }, 1000)
}

async function sendCode() {
  const valid = await formRef.value?.validateField('email').catch(() => false)
  if (!valid) return
  sending.value = true
  try {
    await sendResetCode(form.email)
    ElMessage.success('验证码已发送')
    startCountdown()
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '验证码发送失败')
  } finally {
    sending.value = false
  }
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await resetPassword(form.email, form.newPassword, form.verificationCode)
    ElMessage.success('密码已重置')
    await router.push('/login')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '重置失败')
  } finally {
    submitting.value = false
  }
}

onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <main class="page">
    <div class="panel">
      <h1>重置密码</h1>
      <p class="subtitle">通过邮箱验证码设置新密码</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
        </el-form-item>

        <el-form-item label="验证码" prop="verificationCode">
          <el-input v-model="form.verificationCode" maxlength="6" placeholder="请输入验证码">
            <template #append>
              <el-button :disabled="countdown > 0 || sending" @click="sendCode">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="form.newPassword" type="password" placeholder="至少 8 位" show-password :prefix-icon="Lock" />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入新密码" show-password :prefix-icon="Lock" />
        </el-form-item>

        <el-button class="submit" type="primary" native-type="submit" :loading="submitting">确认修改</el-button>

        <p class="signup">
          <el-link type="primary" :underline="false" @click="router.push('/login')">返回登录</el-link>
        </p>
      </el-form>
    </div>
  </main>
</template>

<style scoped>
.page {
  box-sizing: border-box;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #eef2f6;
}
.panel {
  width: min(100%, 360px);
  padding: 28px 24px 20px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(31, 42, 55, 0.12);
}
h1 {
  margin: 0;
  font-size: 26px;
}
.subtitle {
  margin: 6px 0 18px;
  color: var(--el-text-color-secondary);
}
.submit {
  width: 100%;
}
.signup {
  margin-top: 22px;
  text-align: center;
}
</style>