import { ref, reactive, watch } from 'vue'

const LANG_KEY = 'rag2_language'

// 所有界面文本翻译
const messages = {
  'zh-CN': {
    notes: '笔记',
    aiAssistant: 'AI助手',
    profile: '我的',
    search: '搜索',
    searchPlaceholder: '搜索笔记...',
    all: '全部',
    work: '工作',
    study: '学习',
    life: '生活',
    addCategory: '添加分类',
    addCategoryTitle: '添加分类',
    categoryInputPlaceholder: '输入分类名称（最多4字）',
    categoryFull: '标签栏已满，请删除多余的标签栏后重试',
    categoryExists: '该分类已存在',
    newNote: '新建笔记',
    editNote: '编辑笔记',
    back: '返回',
    save: '保存',
    saveSuccess: '保存成功',
    saveFail: '保存失败',
    delete: '删除',
    deleteConfirm: '确认删除',
    deleteMsg: '删除后不可恢复',
    deleted: '已删除',
    loadFail: '加载失败',
    searchFail: '搜索失败',
    noNotes: '暂无笔记，点击 + 创建',
    noMore: '没有更多了',
    noteTitle: '笔记标题...',
    startWriting: '开始写作...',
    addTag: '添加标签',
    selectTag: '选择标签',
    customTag: '其他（自定义）',
    customTagTitle: '自定义标签',
    customTagPlaceholder: '输入标签名（最多4字）',
    unnamedNote: '未命名笔记',
    noContent: '暂无内容',
    welcome: '我是智能笔记助手',
    welcomeSub: '可以搜索知识库、查找笔记、创建记录',
    quick1: '帮我创建一个学习笔记',
    quick2: '搜索知识库中的内容',
    quick3: '帮我查找最近的笔记',
    inputPlaceholder: '输入消息...',
    send: '发送',
    thinking: '思考过程',
    requestFail: '请求失败',
    chatHistory: '历史会话',
    newSession: '新建会话',
    noSessions: '暂无会话',
    close: '关闭',
    loadSessionFail: '加载会话失败',
    knowledgeBase: '知识库',
    personalization: '个性化',
    aboutUs: '关于我们',
    language: '语言选择',
    theme: '模式选择',
    lightMode: '亮色调',
    darkMode: '暗色调',
    simplifiedChinese: '简体中文',
    english: '英文',
    aboutTitle: 'RAG2 智能笔记助手',
    aboutDesc: '一款基于RAG技术的智能笔记应用，支持知识库检索、AI辅助写作和智能笔记管理。',
    aboutVersion: '版本 1.1.2',
    confirmDeleteSession: '删除后不可恢复，确定要删除该会话吗？',
    tagCannotDelete: '默认分类不可删除',
    knowledgeEmpty: '暂无知识库文档',
    uploadDoc: '上传文档',
    chooseFile: '选择文件',
    upload: '上传',
    uploading: '上传中...',
    uploadSuccess: '上传成功',
    uploadFail: '上传失败',
    docExists: '文档已存在',
    docDeleteConfirm: '确认删除该文档？',
    docClear: '清空知识库',
    docClearConfirm: '确认清空全部文档？',
    viewKnowledge: '查看知识库',
    myKnowledge: '我的知识库',
    langSwitched: '已切换为简体中文',
    darkSwitched: '已切换为暗色调',
    lightSwitched: '已切换为亮色调',
    categoryZhPlaceholder: '中文名称（最多4字）',
    categoryEnPlaceholder: 'English name (max 10)',
    customTagZhPlaceholder: '中文标签（最多4字）',
    customTagEnPlaceholder: 'English tag (max 10)',
  },
  'en': {
    notes: 'Notes',
    aiAssistant: 'AI Chat',
    profile: 'Profile',
    search: 'Search',
    searchPlaceholder: 'Search notes...',
    all: 'All',
    work: 'Work',
    study: 'Study',
    life: 'Life',
    addCategory: 'Add Category',
    addCategoryTitle: 'Add Category',
    categoryInputPlaceholder: 'Category name (max 4 chars)',
    categoryFull: 'Category bar is full. Please remove some categories and try again.',
    categoryExists: 'Category already exists',
    newNote: 'New Note',
    editNote: 'Edit Note',
    back: 'Back',
    save: 'Save',
    saveSuccess: 'Saved successfully',
    saveFail: 'Save failed',
    delete: 'Delete',
    deleteConfirm: 'Confirm Delete',
    deleteMsg: 'This cannot be undone',
    deleted: 'Deleted',
    loadFail: 'Load failed',
    searchFail: 'Search failed',
    noNotes: 'No notes yet. Tap + to create one.',
    noMore: 'No more notes',
    noteTitle: 'Note title...',
    startWriting: 'Start writing...',
    addTag: 'Add Tag',
    selectTag: 'Select Tag',
    customTag: 'Other (Custom)',
    customTagTitle: 'Custom Tag',
    customTagPlaceholder: 'Tag name (max 4 chars)',
    unnamedNote: 'Untitled Note',
    noContent: 'No content',
    welcome: 'I am your Smart Note Assistant',
    welcomeSub: 'Search knowledge base, find notes, create records',
    quick1: 'Help me create a study note',
    quick2: 'Search the knowledge base',
    quick3: 'Find my recent notes',
    inputPlaceholder: 'Type a message...',
    send: 'Send',
    thinking: 'Thinking Process',
    requestFail: 'Request failed',
    chatHistory: 'History',
    newSession: 'New Session',
    noSessions: 'No sessions yet',
    close: 'Close',
    loadSessionFail: 'Failed to load session',
    knowledgeBase: 'Knowledge Base',
    personalization: 'Personalization',
    aboutUs: 'About Us',
    language: 'Language',
    theme: 'Theme',
    lightMode: 'Light Mode',
    darkMode: 'Dark Mode',
    simplifiedChinese: 'Simplified Chinese',
    english: 'English',
    aboutTitle: 'RAG2 Smart Note Assistant',
    aboutDesc: 'An intelligent note-taking app powered by RAG technology, supporting knowledge base search, AI-assisted writing, and smart note management.',
    aboutVersion: 'Version 1.1.2',
    confirmDeleteSession: 'This cannot be undone. Are you sure you want to delete this session?',
    tagCannotDelete: 'Default categories cannot be deleted',
    knowledgeEmpty: 'No documents in knowledge base',
    uploadDoc: 'Upload Document',
    chooseFile: 'Choose File',
    upload: 'Upload',
    uploading: 'Uploading...',
    uploadSuccess: 'Uploaded successfully',
    uploadFail: 'Upload failed',
    docExists: 'Document already exists',
    docDeleteConfirm: 'Are you sure you want to delete this document?',
    docClear: 'Clear Knowledge Base',
    docClearConfirm: 'Are you sure you want to clear all documents?',
    viewKnowledge: 'View Knowledge Base',
    myKnowledge: 'My Knowledge Base',
    langSwitched: 'Switched to Simplified Chinese',
    darkSwitched: 'Switched to Dark Mode',
    lightSwitched: 'Switched to Light Mode',
    categoryZhPlaceholder: 'Chinese name (max 4)',
    categoryEnPlaceholder: 'English name (max 10)',
    customTagZhPlaceholder: 'Chinese tag (max 4)',
    customTagEnPlaceholder: 'English tag (max 10)',
  }
}

// 标签翻译映射：数据库存中文，显示时根据语言翻译
const tagMap = {
  '工作': { 'zh-CN': '工作', 'en': 'Work' },
  '学习': { 'zh-CN': '学习', 'en': 'Study' },
  '生活': { 'zh-CN': '生活', 'en': 'Life' },
}

const CUSTOM_CATS_KEY = 'rag2_custom_categories'

// 加载自定义分类（自动兼容旧格式）
function loadCustomCategories() {
  try {
    const raw = localStorage.getItem(CUSTOM_CATS_KEY)
    if (!raw) return []
    const data = JSON.parse(raw)
    return data.map(c => typeof c === 'string' ? { zh: c, en: c } : c)
  } catch { return [] }
}

// 全局语言状态
const currentLang = ref(localStorage.getItem(LANG_KEY) || 'zh-CN')

export function useI18n() {
  function t(key) {
    return messages[currentLang.value]?.[key] || messages['zh-CN'][key] || key
  }

  function setLang(lang) {
    currentLang.value = lang
    localStorage.setItem(LANG_KEY, lang)
  }

  function getLang() {
    return currentLang.value
  }

  function translateTag(tag) {
    if (tagMap[tag]) return tagMap[tag][currentLang.value] || tag
    const customs = loadCustomCategories()
    const found = customs.find(c => c.zh === tag)
    if (found) return found[currentLang.value] || found.zh || tag
    return tag
  }

  return { t, setLang, getLang, currentLang, translateTag }
}

export { CUSTOM_CATS_KEY, loadCustomCategories }
