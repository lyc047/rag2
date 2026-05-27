const routes = [
  { path: '/', redirect: '/notes' },
  {
    path: '/notes',
    name: 'NoteList',
    component: () => import('../views/NoteList.vue'),
    meta: { title: '笔记' }
  },
  {
    path: '/notes/:id',
    name: 'NoteEditor',
    component: () => import('../views/NoteEditor.vue'),
    meta: { title: '编辑笔记' }
  },
  {
    path: '/chat',
    name: 'AIChat',
    component: () => import('../views/AIChat.vue'),
    meta: { title: 'AI助手' }
  },
  {
    path: '/chat/:sessionId',
    name: 'AIChatSession',
    component: () => import('../views/AIChat.vue'),
    meta: { title: 'AI助手' }
  },
  {
    path: '/knowledge',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: { title: '知识库' }
  },
]

export default routes
