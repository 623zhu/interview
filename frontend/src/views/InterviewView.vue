<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules, UploadRequestOptions } from 'element-plus'
import { ArrowRight, Check, Document, Files, Loading } from '@element-plus/icons-vue'
import { listResumes, uploadResume, type ResumeListItem } from '@/api/resume'
import {
  TARGET_ROLES,
  createInterviewSession,
  listInterviewSessions,
  markSessionTypewriter,
  type Difficulty,
  type InterviewSessionListItem,
  type TargetRole,
} from '@/api/interview'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'
import { formatDate } from '@/utils/datetime'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const uploading = ref(false)
const starting = ref(false)
const resumes = ref<ResumeListItem[]>([])
const activeSession = ref<InterviewSessionListItem | null>(null)

function roleFromQuery(): TargetRole {
  const role = route.query.role
  return TARGET_ROLES.find((item) => item === role) ?? 'Java 后端'
}

const form = reactive({
  resumeId: null as number | null,
  targetRole: roleFromQuery(),
  difficulty: 'medium' as Difficulty,
})

const rules: FormRules = {
  resumeId: [{ required: true, message: '请选择一份可用简历', trigger: 'change' }],
  targetRole: [{ required: true, message: '请选择面试岗位', trigger: 'change' }],
  difficulty: [{ required: true, message: '请选择面试难度', trigger: 'change' }],
}

const statusLabel: Record<string, string> = {
  ready: '可用',
  failed: '解析失败',
}

const difficultyOptions: { value: Difficulty; label: string; desc: string }[] = [
  { value: 'easy', label: '简单', desc: '适合初次练习' },
  { value: 'medium', label: '中等', desc: '贴近常规面试' },
  { value: 'hard', label: '困难', desc: '高阶追问挑战' },
]

const readyResumes = computed(() => resumes.value.filter((item) => item.status === 'ready'))
const recentResumes = computed(() => resumes.value.slice(0, 3))
const canStart = computed(() => Boolean(form.resumeId) && !uploading.value && !starting.value)

function formatTime(value: string) {
  return formatDate(value)
}

function fileKind(row: ResumeListItem) {
  return row.original_filename.toLowerCase().endsWith('.pdf') ? 'pdf' : 'docx'
}

function fileLabel(row: ResumeListItem) {
  return fileKind(row) === 'pdf' ? 'PDF' : 'DOC'
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
      target_role: form.targetRole,
      difficulty: form.difficulty,
    })
    markSessionTypewriter(session.id)
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

        <section class="setup-card">
          <div class="setup-head">
            <div>
              <h2>面试设置</h2>
              <p>大约需要 1 分钟完成配置</p>
            </div>
            <div class="steps">
              <span class="step" :class="{ active: !starting, done: starting }">
                <span class="step-no">1</span>设置
              </span>
              <span class="step-line" />
              <span class="step" :class="{ active: starting }">
                <span class="step-no">2</span>准备
              </span>
            </div>
          </div>

          <el-form
            ref="formRef"
            class="setup"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="startInterview()"
          >
            <div class="setup-row">
              <el-form-item label="目标岗位" prop="targetRole">
                <el-select
                  v-model="form.targetRole"
                  class="role-select"
                  :disabled="starting"
                  placeholder="选择面试岗位"
                >
                  <el-option
                    v-for="role in TARGET_ROLES"
                    :key="role"
                    :label="role"
                    :value="role"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="面试难度" prop="difficulty">
                <div class="levels">
                  <button
                    v-for="item in difficultyOptions"
                    :key="item.value"
                    type="button"
                    class="level"
                    :class="{ active: form.difficulty === item.value }"
                    :disabled="starting"
                    @click="form.difficulty = item.value"
                  >
                    <strong>{{ item.label }}</strong>
                    <span>{{ item.desc }}</span>
                  </button>
                </div>
              </el-form-item>
            </div>

            <el-form-item label="简历" prop="resumeId">
              <div class="resume-row">
                <div class="resume-pick">
                  <div class="upload-icon"><el-icon><Files /></el-icon></div>
                  <div class="upload-main">
                    <strong>使用已上传的简历</strong>
                    <el-select
                      v-model="form.resumeId"
                      class="resume-select"
                      :placeholder="readyResumes.length ? '选择一份可用简历' : '暂无可用简历，请先上传'"
                      :disabled="starting || !readyResumes.length"
                    >
                      <el-option
                        v-for="item in readyResumes"
                        :key="item.id"
                        :label="item.original_filename"
                        :value="item.id"
                      />
                    </el-select>
                  </div>
                </div>

                <el-upload
                  drag
                  class="uploader"
                  :show-file-list="false"
                  :disabled="uploading || starting"
                  accept=".pdf,.docx"
                  :before-upload="beforeUpload"
                  :http-request="onUpload"
                >
                  <div class="upload-box">
                    <div class="upload-icon"><el-icon><Document /></el-icon></div>
                    <div class="upload-main">
                      <strong>
                        {{ uploading ? '正在解析简历…' : '点击选择或拖入简历' }}
                      </strong>
                      <span>支持 PDF、DOCX，文件不超过 10MB</span>
                    </div>
                    <span class="upload-btn">选择文件</span>
                  </div>
                </el-upload>
              </div>
            </el-form-item>

            <div class="setup-foot">
              <span class="foot-note">
                <el-icon><Check /></el-icon>
                {{ starting ? '正在根据简历生成面试计划和第一问…' : '你的面试数据仅用于生成本次练习' }}
              </span>
              <button
                type="submit"
                class="start-btn"
                :class="{ busy: starting }"
                :disabled="!canStart"
              >
                <el-icon v-if="starting" class="is-loading"><Loading /></el-icon>
                {{ starting ? '准备中' : '开始模拟面试' }}
                <el-icon v-if="!starting"><ArrowRight /></el-icon>
              </button>
            </div>
          </el-form>
        </section>

        <section class="resume-card">
          <div class="resume-head">
            <div>
              <h3>我的简历</h3>
              <p>已解析的简历可直接用于创建新的模拟面试</p>
            </div>
            <span v-if="resumes.length" class="resume-badge">只显示最近上传的三份简历</span>
          </div>

          <el-table
            v-if="resumes.length"
            class="resume-table"
            :data="recentResumes"
            row-key="id"
          >
            <el-table-column label="文件名称" min-width="260">
              <template #default="{ row }">
                <div class="file">
                  <span class="file-type" :class="fileKind(row)">{{ fileLabel(row) }}</span>
                  <span class="file-name">{{ row.original_filename }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="解析状态" width="160">
              <template #default="{ row }">
                <span class="status" :class="row.status">
                  <i />{{ statusLabel[row.status] ?? row.status }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="上传时间" width="180">
              <template #default="{ row }">
                <span class="upload-time">{{ formatTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="right">
              <template #default="{ row }">
                <button
                  v-if="row.status === 'ready'"
                  type="button"
                  class="row-start"
                  :disabled="starting"
                  @click="startInterview(row.id)"
                >
                  开始面试
                </button>
                <span v-else class="hint">无法开场</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="还没有简历，上传一份后即可开始面试" />
          <p v-if="resumes.length && !readyResumes.length" class="hint">
            当前没有解析成功的简历，请重新上传后再开场。
          </p>
        </section>
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
.ongoing {
  margin-bottom: 16px;
}
.ongoing-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.resume-card {
  overflow: hidden;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 8px 28px rgba(31, 42, 55, 0.06);
}
.resume-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 28px 18px;
}
.resume-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.resume-head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.resume-badge {
  flex: none;
  padding: 5px 12px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  background: #f0f1f5;
  border-radius: 999px;
}
.resume-table {
  --el-table-header-text-color: var(--el-text-color-secondary);
  --el-table-header-bg-color: #f8f9fb;
}
.resume-table :deep(th.el-table__cell) {
  font-size: 12px;
  font-weight: 500;
}
.resume-table :deep(td.el-table__cell) {
  padding: 18px 0;
}
.resume-table :deep(th.el-table__cell:first-child .cell),
.resume-table :deep(td.el-table__cell:first-child .cell) {
  padding-left: 28px;
}
.resume-table :deep(th.el-table__cell:last-child .cell),
.resume-table :deep(td.el-table__cell:last-child .cell) {
  padding-right: 28px;
}
.file {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.file-type {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 8px;
}
.file-type.pdf {
  color: #e2553f;
  background: #fdeeec;
}
.file-type.docx {
  color: #3b6fe0;
  background: #e9f0fd;
}
.file-name {
  overflow: hidden;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  background: #f0f1f5;
  border-radius: 999px;
}
.status i {
  width: 6px;
  height: 6px;
  background: currentColor;
  border-radius: 50%;
}
.status.ready {
  color: #16a34a;
  background: #e8f8ee;
}
.status.failed {
  color: #dc2626;
  background: #fdecec;
}
.upload-time {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.row-start {
  padding: 8px 16px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  color: #6d5df6;
  background: #efedfe;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.row-start:hover:not(:disabled) {
  background: #e2defd;
}
.row-start:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.resume-card > .hint {
  margin: 0;
  padding: 0 28px 18px;
}

.setup-card {
  --accent: #6d5df6;
  --accent-soft: #efedfe;
  margin-bottom: 16px;
  padding: 26px 28px 24px;
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 8px 28px rgba(31, 42, 55, 0.06);
}
.setup-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f1f5;
}
.setup-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}
.setup-head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.steps {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.step-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 12px;
  font-weight: 600;
  background: #f0f1f5;
  border-radius: 50%;
}
.step.active,
.step.done {
  font-weight: 600;
  color: var(--accent);
}
.step.active .step-no,
.step.done .step-no {
  color: var(--accent);
  background: var(--accent-soft);
}
.step-line {
  width: 40px;
  height: 1px;
  background: #dcdfe6;
}

.setup {
  margin-top: 22px;
}
.setup :deep(.el-form-item__label) {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.setup-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}
.role-select {
  width: 100%;
}
.role-select :deep(.el-select__wrapper) {
  min-height: 44px;
  padding: 0 16px;
  font-size: 15px;
  border-radius: 12px;
}
.levels {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}
.level {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  text-align: left;
  font-family: inherit;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.level strong {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.level span {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.level:hover:not(:disabled) {
  border-color: var(--accent);
}
.level.active {
  background: #f6f5ff;
  border-color: var(--accent);
}
.level.active strong {
  color: var(--accent);
}
.level:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.resume-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  width: 100%;
}
.resume-pick {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 86px;
  padding: 0 18px;
  border: 1px solid #e4e7ed;
  border-radius: 14px;
  box-sizing: border-box;
}
.resume-select {
  width: 100%;
}
.uploader {
  width: 100%;
}
.uploader :deep(.el-upload),
.uploader :deep(.el-upload-dragger) {
  width: 100%;
  height: 100%;
}
.uploader :deep(.el-upload-dragger) {
  display: flex;
  align-items: center;
  min-height: 86px;
  padding: 0 18px;
  box-sizing: border-box;
  background: #fff;
  border: 1px dashed #dcdfe6;
  border-radius: 14px;
}
.uploader :deep(.el-upload-dragger:hover),
.uploader :deep(.el-upload-dragger.is-dragover) {
  border-color: var(--accent);
  background: #fbfaff;
}
.upload-box {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 16px;
  text-align: left;
}
.upload-icon {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  font-size: 20px;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 12px;
}
.upload-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.upload-main strong {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}
.upload-main span {
  overflow: hidden;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-btn {
  flex: none;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  border: 1px solid #dcdfe6;
  border-radius: 8px;
}

.setup-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid #f0f1f5;
}
.foot-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.foot-note .el-icon {
  color: #16a34a;
}
.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0 26px;
  min-height: 48px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: none;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(109, 93, 246, 0.3);
  cursor: pointer;
  transition: background 0.15s ease;
}
.start-btn:hover:not(:disabled) {
  background: #5b4be8;
}
.start-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
}
.start-btn.busy:disabled {
  cursor: progress;
  opacity: 0.85;
}

@media (max-width: 760px) {
  .setup-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .resume-row {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .setup-head,
  .setup-foot {
    flex-direction: column;
    align-items: flex-start;
  }
}
.hint {
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
}
</style>
