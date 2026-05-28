<template>
  <div class="knowledge-page">
    <van-nav-bar :title="t('knowledgeBase')" :left-text="t('back')" left-arrow @click-left="$router.back()" fixed placeholder />

    <!-- 上传区域 -->
    <div class="upload-area card">
      <div class="upload-title">上传文档 (PDF/TXT/DOCX/MD/PPTX)</div>
      <van-uploader :after-read="uploadFiles" accept=".pdf,.txt,.docx,.md,.pptx"
        multiple :max-count="10" :show-upload="false">
        <van-button icon="plus" type="primary" round block>选择文件上传</van-button>
      </van-uploader>

      <!-- 上传进度列表 -->
      <div v-if="uploadList.length > 0" class="upload-progress-list">
        <div v-for="item in uploadList" :key="item.filename" class="upload-item">
          <div class="upload-filename">{{ item.filename }}</div>
          <van-progress :percentage="item.percentage"
            :color="item.status === 'failed' ? 'var(--color-danger)' : 'var(--color-primary)'" />
          <div class="upload-msg" :style="{ color: item.status === 'failed' ? 'var(--color-danger)' : '' }">
            {{ item.message }}</div>
        </div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="doc-list-title">已入库文档 ({{ documents.length }})</div>
    <div v-if="documents.length === 0" class="empty-state">
      <van-empty :description="t('knowledgeEmpty')" />
    </div>
    <div v-for="doc in documents" :key="doc.md5" class="doc-card card"
      @click="viewChunks(doc)">
      <div class="doc-name">{{ doc.filename }}</div>
      <div class="doc-meta">MD5: {{ doc.md5?.substring(0, 16) }}...</div>
      <van-button size="mini" type="danger" @click.stop="deleteDoc(doc.md5)">删除</van-button>
    </div>

    <!-- 文档切片详情弹窗 -->
    <van-popup v-model:show="showChunks" position="bottom" :style="{ height: '70%' }" round>
      <div class="chunk-panel">
        <van-nav-bar title="文档切片" left-text="关闭" @click-left="showChunks = false" />
        <div v-for="(chunk, i) in currentChunks" :key="i" class="chunk-item">
          <div class="chunk-index">切片 #{{ i + 1 }}</div>
          <div class="chunk-text">{{ chunk.content }}</div>
        </div>
        <van-empty v-if="currentChunks.length === 0" description="暂无切片" />
      </div>
    </van-popup>

    <!-- 清空按钮 -->
    <div style="padding: 16px; text-align: center;">
      <van-button type="danger" round plain size="small" @click="clearAll">清空知识库</van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import axios from 'axios'
import API from '../config/api.js'
import { useI18n } from '../composables/useI18n.js'

const { t } = useI18n()

const documents = ref([])
const uploadList = ref([])
const showChunks = ref(false)
const currentChunks = ref([])

// 加载文档列表
onMounted(async () => {
  try {
    const { data } = await axios.get(API.knowledgeDocuments)
    if (data.code === 200) documents.value = data.data || []
  } catch (e) { }
})

// 上传文件（SSE流式进度）
async function uploadFiles(fileList) {
  const formData = new FormData()
  const files = Array.isArray(fileList) ? fileList : [fileList]

  for (const f of files) {
    formData.append('files', f.file || f)
    uploadList.value.push({
      filename: (f.file || f).name, percentage: 0, message: '准备上传...', status: 'uploading'
    })
  }

  try {
    const resp = await fetch(API.knowledgeUpload, { method: 'POST', body: formData })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(line.substring(6))
          const idx = uploadList.value.findIndex(p => p.filename === evt.filename)
          if (idx === -1) continue

          const item = uploadList.value[idx]
          item.message = evt.message || item.message

          if (evt.event_type === 'completed') {
            item.status = 'completed'; item.percentage = 100
          } else if (evt.event_type === 'error') {
            item.status = 'failed'; item.percentage = 0
          } else if (evt.event_type === 'start') {
            item.percentage = 10
          } else if (evt.event_type === 'skipped') {
            item.status = 'completed'; item.percentage = 100; item.message = '已存在，跳过'
          }
        } catch (e) { /* */ }
      }
    }
    await loadDocuments()
  } catch (e) { showToast('上传失败') }
}

// 查看切片
async function viewChunks(doc) {
  try {
    const { data } = await axios.get(API.knowledgeChunks(doc.md5))
    if (data.code === 200) {
      currentChunks.value = data.data.chunks || []
      showChunks.value = true
    }
  } catch (e) { showToast('加载切片失败') }
}

// 删除文档
async function deleteDoc(md5) {
  try { await showConfirmDialog({ title: '确认删除此文档？' })
    await axios.delete(API.knowledgeDelete(md5))
    await loadDocuments()
    showToast('已删除')
  } catch (e) { /* 取消 */ }
}

// 清空
async function clearAll() {
  try { await showConfirmDialog({ title: '确认清空整个知识库？', message: '此操作不可恢复' })
    await axios.delete(API.knowledgeClear)
    documents.value = []
    showToast('已清空')
  } catch (e) { /* 取消 */ }
}

async function loadDocuments() {
  try {
    const { data } = await axios.get(API.knowledgeDocuments)
    if (data.code === 200) documents.value = data.data || []
  } catch (e) { }
}
</script>

<style scoped>
.upload-area { text-align: center; }
.upload-title { font-size: 14px; margin-bottom: 12px; color: var(--color-text-light); }
.upload-progress-list { margin-top: 16px; }
.upload-item { margin-bottom: 12px; text-align: left; }
.upload-filename { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.upload-msg { font-size: 11px; color: var(--color-text-light); margin-top: 2px; }

.doc-list-title { font-size: 15px; font-weight: 600; padding: 16px 16px 8px; }
.doc-card { display: flex; align-items: center; gap: 10px; }
.doc-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { font-size: 11px; color: var(--color-text-light); }

.chunk-panel { height: 100%; overflow-y: auto; padding-bottom: 20px; }
.chunk-item { padding: 12px 16px; border-bottom: 1px solid var(--color-border); }
.chunk-index { font-size: 12px; color: var(--color-primary); margin-bottom: 4px; }
.chunk-text { font-size: 13px; line-height: 1.6; color: var(--color-text); }
</style>
