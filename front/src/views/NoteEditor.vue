<template>
  <div class="note-editor-page">
    <van-nav-bar :title="isNew ? '新建笔记' : '编辑笔记'" left-text="返回" left-arrow
      @click-left="goBack">
      <template #right>
        <van-icon name="delete-o" size="20" @click="confirmDelete" v-if="!isNew" />
        <span style="color:var(--accent);cursor:pointer" @click="saveNote">保存</span>
      </template>
    </van-nav-bar>

    <!-- 标题 -->
    <div class="editor-title">
      <input v-model="title" placeholder="笔记标题..." class="title-input" />
    </div>

    <!-- 标签 -->
    <div class="editor-tags">
      <van-tag v-for="(tag, i) in tags" :key="i" closeable size="medium"
        type="primary" @close="removeTag(i)">{{ tag }}</van-tag>
      <van-button size="small" icon="plus" round @click="showTagInput = true">添加标签</van-button>
    </div>

    <!-- 内容编辑器 -->
    <div class="editor-content">
      <textarea ref="contentRef" v-model="content" placeholder="开始写作..."
        class="content-textarea"></textarea>
    </div>

    <!-- 添加标签弹窗 -->
    <van-dialog v-model:show="showTagInput" title="添加标签" show-cancel-button
      @confirm="addTag">
      <div class="tag-dialog">
        <input v-model="newTag" placeholder="输入标签名" class="tag-input" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import axios from 'axios'
import API from '../config/api.js'

const router = useRouter()
const route = useRoute()
const noteId = route.params.id
const isNew = noteId === 'new'

const title = ref('')
const content = ref('')
const tags = ref([])
const newTag = ref('')
const showTagInput = ref(false)

// 加载笔记
onMounted(async () => {
  if (!isNew) {
    try {
      const { data } = await axios.get(API.noteDetail(noteId))
      if (data.code === 200 && data.data) {
        title.value = data.data.title
        content.value = data.data.content
        tags.value = data.data.tags || []
      }
    } catch (e) { showToast('加载笔记失败') }
  }
})

// 保存
async function saveNote() {
  try {
    const payload = { title: title.value || '未命名笔记', content: content.value, tags: tags.value }
    if (isNew) {
      await axios.post(API.noteCreate, payload)
    } else {
      await axios.put(API.noteUpdate(noteId), payload)
    }
    showToast('保存成功')
    router.back()
  } catch (e) { showToast('保存失败') }
}

// 删除
async function confirmDelete() {
  try {
    await showConfirmDialog({ title: '确认删除', message: '删除后不可恢复' })
    await axios.delete(API.noteDelete(noteId))
    showToast('已删除')
    router.back()
  } catch (e) { /* 取消 */ }
}

function addTag() {
  if (newTag.value && !tags.value.includes(newTag.value)) {
    tags.value.push(newTag.value)
  }
  newTag.value = ''
  showTagInput.value = false
}
function removeTag(i) { tags.value.splice(i, 1) }
function goBack() { router.back() }
</script>

<style scoped>
.editor-title { padding: 12px 16px; background: var(--bg-card); }
.title-input { width: 100%; border: none; font-size: 20px; font-weight: 600;
  background: transparent; outline: none; font-family: inherit; }
.editor-tags { display: flex; gap: 6px; padding: 8px 16px; flex-wrap: wrap;
  background: var(--bg-card); border-bottom: 1px solid var(--border); }
.editor-content { flex: 1; display: flex; }
.content-textarea { width: 100%; min-height: calc(100vh - 200px); border: none;
  padding: 16px; font-size: 15px; line-height: 1.8; resize: none; outline: none;
  font-family: inherit; background: var(--bg-card); }
.tag-dialog { padding: 20px; }
.tag-input { width: 100%; border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 12px; font-size: 14px; outline: none; }
</style>
