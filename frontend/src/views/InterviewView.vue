<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { listResumes, uploadResume, type ResumeListItem } from '@/api/resume'
import { ApiError } from '@/api/http'
import AppHeader from '@/components/AppHeader.vue'

const loading = ref(false)
const uploading = ref(false)
const resumes = ref<ResumeListItem[]>([])

const statusLabel: Record<string, string> = {
  ready: '可用',
  failed: '解析失败',
}
const statusType: Record<string, 'success' | 'danger' | 'info'> = {
  ready: 'success',
  failed: 'danger',
}

const readyResumes = computed(() => resumes.value.filter((item) => item.status === 'ready'))

function formatTime(value: string) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

async function loadResumes(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    resumes.value = await listResumes()
  } catch (error) {
    resumes.value = []
    ElMessage.error(error instanceof ApiError ? error.message : '加载简历失败')
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
      ElMessage.success('简历已上传，可用于开始面试')
    }
    await loadResumes(false)
  } catch (error) {
    ElMessage.error(error instanceof ApiError ? error.message : '上传失败')
  } finally {
    uploading.value = false
  }
}

onMounted(loadResumes)
</script>

<template>
  <div class="layout">
    <AppHeader />

    <main v-loading="loading" class="main">
      <div class="content">
        <div class="intro">
          <h1>模拟面试</h1>
          <p>先上传 PDF 或 Word 简历，解析成功后即可用来开场。</p>
        </div>

        <el-card class="panel" shadow="never">
          <el-upload
            drag
            :show-file-list="false"
            :disabled="uploading"
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
        </el-card>

        <el-card class="panel" shadow="never">
          <template #header>已上传的简历</template>
          <el-table v-if="resumes.length" :data="resumes">
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
.panel {
  margin-bottom: 16px;
  border-radius: 12px;
}
.upload-text {
  padding: 24px 0 8px;
  color: var(--el-text-color-regular);
}
.hint {
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
}
</style>
