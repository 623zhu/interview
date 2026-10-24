<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, UploadRequestOptions } from 'element-plus'
import { listResumes, uploadResume, type ResumeListItem } from '@/api/resume'
import {
  createInterviewSession,
  listInterviewSessions,
  type Difficulty,
  type InterviewSessionListItem,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const uploading = ref(false)
const starting = ref(false)
const resumes = ref<ResumeListItem[]>([])
const activeSession = ref<InterviewSessionListItem | null>(null)

const form = reactive({
  resumeId: null as number | null,
  targetRole: 'Java 后端',
  difficulty: 'medium' as Difficulty,
})

const rules: FormRules = {
  resumeId: [{ required: true, message: '请选择一份可用简历', trigger: 'change' }],
  targetRole: [
    { required: true, message: '请填写面试岗位', trigger: 'blur' },
    { min: 1, max: 128, message: '岗位名称不超过 128 字', trigger: 'blur' },
  ],
  difficulty: [{ required: true, message: '请选择面试难度', trigger: 'change' }],
}

const statusLabel: Record<string, string> = {
  ready: '可用',
  failed: '解析失败',
}
const statusType: Record<string, 'success' | 'danger' | 'info'> = {
  ready: 'success',
  failed: 'danger',
}

const readyResumes = computed(() => resumes.value.filter((item) => item.status === 'ready'))
const canStart = computed(() => Boolean(form.resumeId) && !uploading.value && !starting.value)

function formatTime(value: string) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function selectResume(row: ResumeListItem) {
  if (row.status === 'ready') {
    form.resumeId = row.id
  }
}

async function loadPage() {
  loading.value = true
  try {
    const [resumeList, inProgress] = await Promise.all([
      listResumes(),
      listInterviewSessions({ status: 'in_progress', limit: 1 }),
    ])
    resumes.value = resumeList
    activeSession.value = inProgress[0] ?? null
    if (form.resumeId && !readyResumes.value.some((item) => item.id === form.resumeId)) {
      form.resumeId = null
    }
    const firstReady = readyResumes.value[0]
    if (!form.resumeId && firstReady) {
      form.resumeId = firstReady.id
    }
  } catch (error) {
    resumes.value = []
    activeSession.value = null
    ElMessage.error(error instanceof ApiError ? error.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function beforeUpload(file: File) {
  const name = file.name.toLowerCase()
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {
    ElMessage.error('只支持 PDF 或 DOCX')
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件不能超过 10MB')
    return false
  }
  return true
}

async function onUpload({ file }: UploadRequestOptions) {
  uploading.value = true
  try {
    const result = await uploadResume(file)
    if (result.status === 'failed') {
      ElMessage.error(result.error_detail || '简历解析失败')
    } else {
      ElMessage.success('简历已上传，可直接开始面试')
      form.resumeId = result.id
    }
    const resumeList = await listResumes()
    resumes.value = resumeList
    if (result.status === 'ready') {
      form.resumeId = result.id
    }
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

async function startInterview(resumeId = form.resumeId) {
  if (resumeId) form.resumeId = resumeId
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !form.resumeId) return

  starting.value = true
  try {
    const session = await createInterviewSession({
      resume_id: form.resumeId,
      target_role: form.targetRole.trim(),
      difficulty: form.difficulty,
    })
    await router.push(`/interview/${session.id}`)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '开始面试失败')
  } finally {
    starting.value = false
  }
}

function continueInterview() {
  if (activeSession.value) {
    void router.push(`/interview/${activeSession.value.id}`)
  }
}

onMounted(loadPage)
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div class="content">
        <div class="intro">
          <h1>模拟面试</h1>
          <p>在同一个设置里上传或选择简历，填好岗位和难度后开场。</p>
        </div>

        <el-alert
          v-if="activeSession"
          class="ongoing"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #title>
            <div class="ongoing-row">
              <span>
                有一场进行中的面试（{{ activeSession.target_role }}）
              </span>
              <el-button type="warning" size="small" @click="continueInterview">继续面试</el-button>
            </div>
          </template>
        </el-alert>

        <el-card class="panel" shadow="never">
          <template #header>
            <div class="card-header">
              <div>开始模拟面试</div>
              <p>生成第一问需要一点时间，请等场次创建完成后再作答。</p>
            </div>
          </template>

          <el-form
            ref="formRef"
            class="setup"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="startInterview()"
          >
            <el-row :gutter="24">
              <el-col :xs="24" :md="11">
                <el-form-item label="上传简历">
                  <el-upload
                    drag
                    class="uploader"
                    :show-file-list="false"
                    :disabled="uploading || starting"
                    accept=".pdf,.docx"
                    :before-upload="beforeUpload"
                    :http-request="onUpload"
                  >
                    <div class="upload-text">
                      {{ uploading ? '正在解析简历…' : '将简历拖到此处，或点击上传' }}
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">仅支持 .pdf、.docx，不超过 10MB</div>
                    </template>
                  </el-upload>
                </el-form-item>
              </el-col>

              <el-col :xs="24" :md="13">
                <el-form-item label="已上传的简历" prop="resumeId">
                  <el-select
                    v-model="form.resumeId"
                    placeholder="选择一份可用简历"
                    :disabled="starting"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="item in readyResumes"
                      :key="item.id"
                      :label="item.original_filename"
                      :value="item.id"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="面试岗位" prop="targetRole">
                  <el-input
                    v-model="form.targetRole"
                    maxlength="128"
                    :disabled="starting"
                    placeholder="例如：Java 后端"
                  />
                </el-form-item>

                <el-form-item label="面试难度" prop="difficulty">
                  <el-radio-group v-model="form.difficulty" :disabled="starting">
                    <el-radio-button value="easy">简单</el-radio-button>
                    <el-radio-button value="medium">中等</el-radio-button>
                    <el-radio-button value="hard">困难</el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <el-button
                  type="primary"
                  native-type="submit"
                  :loading="starting"
                  :disabled="!canStart"
                >
                  开始面试
                </el-button>
                <p v-if="!readyResumes.length" class="hint">上传并解析成功后即可开场。</p>
              </el-col>
            </el-row>
          </el-form>
        </el-card>

        <el-card class="panel" shadow="never">
          <template #header>已上传的简历</template>
          <el-table
            v-if="resumes.length"
            :data="resumes"
            highlight-current-row
            :current-row-key="form.resumeId ?? undefined"
            row-key="id"
            @row-click="selectResume"
          >
            <el-table-column prop="original_filename" label="文件名" min-width="180" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusType[row.status] ?? 'info'" size="small">
                  {{ statusLabel[row.status] ?? row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="上传时间" width="140">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'ready'"
                  type="primary"
                  link
                  :disabled="starting"
                  @click.stop="startInterview(row.id)"
                >
                  开始面试
                </el-button>
                <span v-else class="hint">无法开场</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="还没有简历，上传一份后即可开始面试" />
          <p v-if="resumes.length && !readyResumes.length" class="hint">
            当前没有解析成功的简历，请重新上传后再开场。
          </p>
        </el-card>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  background: #eef2f6;
}
.main {
  padding: 28px 24px 48px;
}
.content {
  max-width: 1080px;
  margin: 0 auto;
}
.intro h1 {
  margin: 0;
  font-size: 26px;
}
.intro p {
  margin: 8px 0 20px;
  color: var(--el-text-color-secondary);
}
.ongoing {
  margin-bottom: 16px;
}
.ongoing-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.panel {
  margin-bottom: 16px;
  border-radius: 12px;
}
.card-header p {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.setup :deep(.el-upload) {
  width: 100%;
}
.setup :deep(.el-upload-dragger) {
  width: 100%;
  padding: 28px 16px;
}
.upload-text {
  color: var(--el-text-color-regular);
}
.hint {
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
}
</style>
