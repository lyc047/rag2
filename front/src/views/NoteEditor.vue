<template>
  <div class="note-editor-page">
    <van-nav-bar :title="isNew ? t('newNote') : t('editNote')" :left-text="t('back')" left-arrow
      @click-left="goBack">
      <template #right>
        <van-icon name="delete-o" size="20" @click="confirmDelete" v-if="!isNew" />
        <span style="color:var(--color-primary);cursor:pointer" @click="saveNote">{{ t('save') }}</span>
      </template>
    </van-nav-bar>

    <!-- 标题 -->
    <div class="editor-title">
      <input v-model="title" :placeholder="t('noteTitle')" class="title-input" />
    </div>

    <!-- 标签 -->
    <div class="editor-tags">
      <van-tag v-for="(tag, i) in tags" :key="i" closeable size="medium"
        type="primary" @close="removeTag(i)">{{ translateTag(tag) }}</van-tag>
      <van-button size="small" icon="plus" round @click="showTagSheet = true">{{ t('addTag') }}</van-button>
    </div>

    <!-- 内容编辑器 -->
    <div class="editor-content">
      <textarea ref="contentRef" v-model="content" :placeholder="t('startWriting')"
        class="content-textarea"></textarea>
    </div>

    <!-- 添加标签弹窗 -->
    <van-action-sheet v-model:show="showTagSheet" :title="t('selectTag')">
      <div class="tag-sheet">
        <div v-for="cat in availableCategories" :key="cat" class="tag-option"
          @click="selectTag(cat)">{{ translateTag(cat) }}</div>
        <div class="tag-option tag-other" @click="openCustomTag">{{ t('customTag') }}</div>
      </div>
    </van-action-sheet>

    <!-- 自定义标签弹窗 -->
    <van-dialog v-model:show="showCustomTag" :title="t('customTagTitle')" show-cancel-button
      @confirm="addCustomTag">
      <div class="tag-dialog">
        <input v-model="newTagZh" :placeholder="t('customTagZhPlaceholder')" maxlength="4"
          class="tag-input" />
        <input v-model="newTagEn" :placeholder="t('customTagEnPlaceholder')" maxlength="10"
          class="tag-input" style="margin-top:10px" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import axios from 'axios'
import API from '../config/api.js'
import { useI18n, loadCustomCategories } from '../composables/useI18n.js'

const { t, translateTag } = useI18n()
const router = useRouter()
const route = useRoute()
const noteId = route.params.id
const isNew = noteId === 'new'

const title = ref('')
const content = ref('')
const tags = ref([])
const newTagZh = ref('')
const newTagEn = ref('')
const showTagSheet = ref(false)
const showCustomTag = ref(false)

// 加载所有可用分类（默认 + 自定义），返回 zh 值列表
function getAvailableTagValues() {
  const defaults = ['工作', '学习', '生活']
  const customs = loadCustomCategories()
  return [...defaults, ...customs.map(c => c.zh)]
}

const availableCategories = computed(() => {
  return getAvailableTagValues().filter(c => !tags.value.includes(c))
})

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
    } catch (e) { showToast(t('loadFail')) }
  } else {
    // 新建笔记时，若从分类页跳转过来，自动预填分类标签
    const category = route.query.category
    if (category && !tags.value.includes(category)) {
      tags.value = [category]
    }
  }
})

// 保存
async function saveNote() {
  try {
    const payload = { title: title.value || t('unnamedNote'), content: content.value, tags: tags.value }
    if (isNew) {
      await axios.post(API.noteCreate, payload)
    } else {
      await axios.put(API.noteUpdate(noteId), payload)
    }
    showToast(t('saveSuccess'))
    router.back()
  } catch (e) { showToast(t('saveFail')) }
}

// 删除
async function confirmDelete() {
  try {
    await showConfirmDialog({ title: t('deleteConfirm'), message: t('deleteMsg') })
    await axios.delete(API.noteDelete(noteId))
    showToast(t('deleted'))
    router.back()
  } catch (e) { /* 取消 */ }
}

function selectTag(cat) {
  if (!tags.value.includes(cat)) {
    tags.value = [...tags.value, cat]
  }
  showTagSheet.value = false
}
function openCustomTag() {
  showTagSheet.value = false
  newTagZh.value = ''
  newTagEn.value = ''
  showCustomTag.value = true
}
function addCustomTag() {
  const zh = newTagZh.value.trim()
  if (zh && !tags.value.includes(zh)) {
    tags.value = [...tags.value, zh]
  }
  newTagZh.value = ''
  newTagEn.value = ''
  showCustomTag.value = false
}
function removeTag(i) { tags.value.splice(i, 1) }
function goBack() { router.back() }
</script>

<style scoped>
.editor-title { padding: 12px 16px; background: var(--color-card); }
.title-input { width: 100%; border: none; font-size: 20px; font-weight: 600;
  background: transparent; outline: none; font-family: inherit; }
.editor-tags { display: flex; gap: 6px; padding: 8px 16px; flex-wrap: wrap;
  background: var(--color-card); border-bottom: 1px solid var(--color-border); }
.editor-content { flex: 1; display: flex; }
.content-textarea { width: 100%; min-height: calc(100vh - 200px); border: none;
  padding: 16px; font-size: 15px; line-height: 1.8; resize: none; outline: none;
  font-family: inherit; background: var(--color-card); }
.tag-sheet { padding: 0 16px 20px; }
.tag-option { padding: 14px 0; text-align: center; font-size: 15px;
  border-bottom: 1px solid var(--color-border); cursor: pointer; }
.tag-option:active { background: var(--color-surface); }
.tag-other { color: var(--color-primary); font-weight: 500; }
.tag-dialog { padding: 20px; }
.tag-input { width: 100%; border: 1px solid var(--color-border); border-radius: 8px;
  padding: 8px 12px; font-size: 14px; outline: none; }
</style>
