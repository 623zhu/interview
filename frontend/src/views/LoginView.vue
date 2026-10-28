<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/http'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ email: '', password: '' })

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await authStore.login(form.email, form.password)
    await router.push('/home')
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="page">
    <div class="panel">
      <h1>欢迎回来</h1>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password :prefix-icon="Lock" />
        </el-form-item>

        <div class="row">
          <el-link type="primary" :underline="false" @click="router.push('/reset-password')">忘记密码?</el-link>
        </div>

        <el-button class="submit" type="primary" native-type="submit" :loading="submitting">登陆</el-button>

        <p class="signup">
          没有账号?
          <el-link type="primary" :underline="false" @click="router.push('/signup')">立即注册</el-link>
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
  margin: 0 0 18px;
  font-size: 26px;
}
.row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 18px;
}
.submit {
  width: 100%;
}
.signup {
  margin-top: 22px;
  text-align: center;
}
</style>