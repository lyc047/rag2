<template>
  <div class="note-list-page">
    <van-nav-bar title="笔记" fixed placeholder>
      <template #right>
        <van-icon name="plus" size="22" @click="goCreate" />
      </template>
    </van-nav-bar>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <van-search v-model="keyword" placeholder="搜索笔记..." shape="round"
        @search="onSearch" @clear="loadNotes" />
    </div>

    <!-- 分类筛选 -->
    <div class="category-filter">
      <van-tag v-for="cat in categories" :key="cat.value"
        :type="cat.value === activeCategory ? 'primary' : 'default'"
        size="medium" @click="switchCategory(cat.value)">{{ cat.label }}</van-tag>
    </div>

    <!-- 笔记列表 -->
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list v-model:loading="loading" :finished="finished"
        finished-text="没有更多了" @load="loadNotes">
        <div v-for="note in notes" :key="note.id" class="note-card card"
          @click="goEdit(note.id)">
          <div class="note-title">{{ note.title }}</div>
          <div class="note-preview">{{ note.content_preview || '暂无内容' }}</div>
          <div class="note-meta">
            <div class="note-tags">
              <van-tag v-for="tag in note.tags" :key="tag" size="mini" type="primary">{{ tag }}</van-tag>
            </div>
            <span class="note-date">{{ formatDate(note.updated_at) }}</span>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>

    <!-- 空状态 -->
    <div v-if="!loading && notes.length === 0" class="empty-state">
      <van-empty description="暂无笔记，点击 + 创建" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import axios from 'axios'
import API from '../config/api.js'

const router = useRouter()
const notes = ref([])
const keyword = ref('')
const activeCategory = ref('')
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

const categories = [
  { label: '全部', value: '' },
  { label: '工作', value: '工作' },
  { label: '学习', value: '学习' },
  { label: '生活', value: '生活' },
]

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
    showToast('加载失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

// 搜索
async function onSearch() {
  if (!keyword.value) { loadNotes(); return }
  try {
    const { data } = await axios.get(API.noteSearch(keyword.value))
    if (data.code === 200) notes.value = data.data
  } catch (e) { showToast('搜索失败') }
}

function onRefresh() { refreshing.value = true; loadNotes() }
function switchCategory(cat) { activeCategory.value = cat; onRefresh() }
function goCreate() { router.push('/notes/new') }
function goEdit(id) { router.push(`/notes/${id}`) }
function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '' }
</script>

<style scoped>
.search-bar { padding: 8px 12px 0; }
.category-filter { display: flex; gap: 8px; padding: 8px 16px; flex-wrap: wrap; }
.note-card { cursor: pointer; transition: transform 0.1s; }
.note-card:active { transform: scale(0.98); }
.note-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.note-preview { font-size: 13px; color: var(--text-secondary); margin-bottom: 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.note-meta { display: flex; justify-content: space-between; align-items: center; }
.note-tags { display: flex; gap: 4px; }
.note-date { font-size: 12px; color: var(--text-secondary); }
</style>
