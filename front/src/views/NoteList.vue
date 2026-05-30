<template>
  <div class="note-list-page">
    <van-nav-bar :title="t('notes')" fixed placeholder>
      <template #right>
        <span v-if="notes.length > 0" class="nav-action" @click="toggleEditMode" style="margin-right:16px">
          {{ editMode ? t('done') : t('edit') }}
        </span>
        <van-icon name="plus" size="22" @click="goCreate" />
      </template>
    </van-nav-bar>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <van-search v-model="keyword" :placeholder="t('searchPlaceholder')" shape="round"
        show-action @search="onSearch" @clear="loadNotes">
        <template #action>
          <div @click="onSearch" style="color:var(--color-primary);padding:0 4px">{{ t('search') }}</div>
        </template>
      </van-search>
    </div>

    <!-- 分类筛选 -->
    <div class="category-filter">
      <van-tag v-for="cat in allCategories" :key="cat.value"
        :type="cat.value === activeCategory ? 'primary' : 'default'"
        size="medium" :closeable="cat.custom"
        @click="switchCategory(cat.value)" @close="removeCategory(cat.value)">
        {{ cat.label }}
      </van-tag>
      <van-tag v-if="allCategories.length < 8" type="default" size="medium"
        class="add-category-btn" @click="showAddCategory = true">＋</van-tag>
    </div>

    <!-- 添加分类弹窗 -->
    <van-dialog v-model:show="showAddCategory" :title="t('addCategoryTitle')" show-cancel-button
      @confirm="addCategory">
      <div class="add-category-body">
        <input v-model="newCategoryZh" :placeholder="t('categoryZhPlaceholder')"
          maxlength="4" class="add-category-input"
          @input="onZhInput" />
        <input v-model="newCategoryEn" :placeholder="t('categoryEnPlaceholder')"
          maxlength="10" class="add-category-input" style="margin-top:10px"
          @input="onEnInput" />
      </div>
    </van-dialog>

    <!-- 编辑模式操作栏 -->
    <div v-if="editMode && notes.length > 0" class="edit-bar">
      <van-button size="small" @click="selectAllNotes">{{ t('selectAll') }}</van-button>
      <van-button size="small" @click="selectedNotes = []">{{ t('deselectAll') }}</van-button>
      <van-button size="small" type="danger" :disabled="selectedNotes.length === 0"
        @click="deleteSelectedNotes">{{ t('deleteSelected') }} ({{ selectedNotes.length }})</van-button>
    </div>

    <!-- 笔记列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh" :style="{ paddingTop: editMode ? '0' : '0' }">
      <van-list v-model:loading="loading" :finished="finished"
        :finished-text="t('noMore')" @load="loadNotes">
        <div v-for="note in notes" :key="note.id" class="note-card card"
          :class="{ 'note-edit-mode': editMode, 'note-selected': selectedNotes.includes(note.id) }"
          @click="editMode ? toggleNoteSelect(note.id) : goEdit(note.id)">
          <van-checkbox v-if="editMode" :model-value="selectedNotes.includes(note.id)"
            @click.stop="toggleNoteSelect(note.id)" class="note-checkbox" />
          <div class="note-body">
            <div class="note-title" v-html="highlight(note.title)"></div>
            <div class="note-preview" v-html="highlight(note.content_preview || t('noContent'))"></div>
            <div class="note-meta">
              <div class="note-tags">
                <van-tag v-for="tag in note.tags" :key="tag" size="mini" type="primary">{{ translateTag(tag) }}</van-tag>
              </div>
              <span class="note-date">{{ formatDate(note.updated_at) }}</span>
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>

    <!-- 空状态 -->
    <div v-if="!loading && notes.length === 0" class="empty-state">
      <van-empty :description="t('noNotes')" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import axios from 'axios'
import API from '../config/api.js'
import { useI18n, CUSTOM_CATS_KEY, loadCustomCategories } from '../composables/useI18n.js'

const MAX_CATEGORIES = 8

const { t, translateTag, currentLang } = useI18n()
const router = useRouter()
const notes = ref([])
const keyword = ref('')
const activeCategory = ref('')
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const editMode = ref(false)
const selectedNotes = ref([])
const page = ref(1)
const showAddCategory = ref(false)
const newCategoryZh = ref('')
const newCategoryEn = ref('')

function defaultCategories() {
  return [
    { label: t('all'), value: '' },
    { label: t('work'), value: '工作' },
    { label: t('study'), value: '学习' },
    { label: t('life'), value: '生活' },
  ]
}

const customCategories = ref(loadCustomCategories())

const allCategories = computed(() => [
  ...defaultCategories(),
  ...customCategories.value.map(c => ({
    label: currentLang.value === 'en' ? c.en : c.zh,
    value: c.zh,
    custom: true,
  })),
])

// 持久化自定义分类
watch(customCategories, (val) => {
  localStorage.setItem(CUSTOM_CATS_KEY, JSON.stringify(val))
}, { deep: true })

function onZhInput(e) {
  if (/[a-zA-Z]/.test(newCategoryZh.value)) {
    showToast('此处只允许输入中文')
    newCategoryZh.value = newCategoryZh.value.replace(/[a-zA-Z]/g, '')
  }
}

function onEnInput(e) {
  if (/[一-鿿]/.test(newCategoryEn.value)) {
    showToast('此处只允许输入英文')
    newCategoryEn.value = newCategoryEn.value.replace(/[一-鿿]/g, '')
  }
}

function addCategory() {
  const zh = newCategoryZh.value.trim()
  const en = newCategoryEn.value.trim() || zh
  if (!zh) return
  if (allCategories.value.length >= MAX_CATEGORIES) {
    showToast(t('categoryFull'))
    newCategoryZh.value = ''; newCategoryEn.value = ''
    return
  }
  if (allCategories.value.some(c => c.value === zh)) {
    showToast(t('categoryExists'))
    newCategoryZh.value = ''; newCategoryEn.value = ''
    return
  }
  customCategories.value = [...customCategories.value, { zh, en }]
  newCategoryZh.value = ''; newCategoryEn.value = ''
}

function removeCategory(value) {
  customCategories.value = customCategories.value.filter(c => c.zh !== value)
  if (activeCategory.value === value) {
    activeCategory.value = ''
    onRefresh()
  }
}

// 加载笔记列表
async function loadNotes() {
  if (refreshing.value) { page.value = 1; notes.value = [] }
  loading.value = true
  try {
    const params = { page: page.value, page_size: 20 }
    if (activeCategory.value) params.category = activeCategory.value
    const { data } = await axios.get(API.noteList, { params })
    if (data.code === 200) {
      const { items, total } = data.data
      notes.value = page.value === 1 ? items : [...notes.value, ...items]
      finished.value = notes.value.length >= total
      page.value++
    }
  } catch (e) {
    showToast(t('loadFail'))
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// 搜索
async function onSearch() {
  if (!keyword.value) { loadNotes(); return }
  try {
    const params = {}
    if (activeCategory.value) params.category = activeCategory.value
    const { data } = await axios.get(API.noteSearch(keyword.value), { params })
    if (data.code === 200) notes.value = data.data
  } catch (e) { showToast(t('searchFail')) }
}

function onRefresh() { refreshing.value = true; loadNotes() }
function switchCategory(cat) { activeCategory.value = cat; onRefresh() }
function toggleEditMode() {
  editMode.value = !editMode.value
  selectedNotes.value = []
}
function toggleNoteSelect(id) {
  const idx = selectedNotes.value.indexOf(id)
  if (idx > -1) selectedNotes.value.splice(idx, 1)
  else selectedNotes.value.push(id)
}
function selectAllNotes() {
  selectedNotes.value = notes.value.map(n => n.id)
}
async function deleteSelectedNotes() {
  if (selectedNotes.value.length === 0) return
  try {
    await showConfirmDialog({ title: t('deleteSelected'), message: t('confirmDeleteSelected') })
  } catch (e) { return /* 用户取消 */ }
  try {
    await axios.post(API.noteBatchDelete, { ids: selectedNotes.value })
    selectedNotes.value = []
    editMode.value = false
    onRefresh()
    showToast(t('deleted'))
  } catch (e) {
    showToast(t('requestFail'))
  }
}
function goCreate() {
  const query = activeCategory.value ? { category: activeCategory.value } : {}
  router.push({ path: '/notes/new', query })
}
function goEdit(id) { router.push(`/notes/${id}`) }
function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '' }
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function highlight(text) {
  if (!keyword.value) return escapeHtml(text)
  const escaped = escapeHtml(text)
  // 转义关键词中的正则特殊字符
  const kw = keyword.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return escaped.replace(new RegExp(kw, 'gi'), '<mark>$&</mark>')
}
</script>

<style scoped>
.nav-action { font-size: 14px; color: var(--color-primary); cursor: pointer; }
.search-bar { padding: 8px 12px 0; }
.category-filter { display: flex; gap: 8px; padding: 8px 16px; flex-wrap: wrap; align-items: center; }
.add-category-btn { cursor: pointer; opacity: 0.6; }
.add-category-btn:active { opacity: 1; }
.add-category-body { padding: 20px; }
.add-category-input { width: 100%; border: 1px solid var(--color-border); border-radius: 8px;
  padding: 8px 12px; font-size: 15px; outline: none; box-sizing: border-box;
  background: var(--color-bg); color: var(--color-text-lighter); }
.add-category-input::placeholder { color: var(--color-text-lighter); opacity: 0.6; }
.edit-bar { display: flex; gap: 8px; padding: 8px 16px; flex-wrap: wrap;
  background: var(--color-card); border-bottom: 1px solid var(--color-border);
  position: sticky; top: 92px; z-index: 10; }
.note-card { cursor: pointer; transition: transform 0.1s; display: flex; align-items: flex-start; gap: 10px; }
.note-card:active { transform: scale(0.98); }
.note-card.note-edit-mode { cursor: default; }
.note-card.note-edit-mode:active { transform: none; }
.note-card.note-selected { background: rgba(212, 145, 74, 0.15);
  box-shadow: inset 3px 0 0 0 var(--color-primary); }
.note-checkbox { flex-shrink: 0; margin-top: 2px; }
.note-body { flex: 1; min-width: 0; }
.note-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.note-title :deep(mark), .note-preview :deep(mark) { background: var(--color-primary); color: #fff; padding: 1px 3px; border-radius: 2px; }
.note-preview { font-size: 13px; color: var(--color-text-light); margin-bottom: 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.note-meta { display: flex; justify-content: space-between; align-items: center; }
.note-tags { display: flex; gap: 4px; }
.note-date { font-size: 12px; color: var(--color-text-light); }
</style>
