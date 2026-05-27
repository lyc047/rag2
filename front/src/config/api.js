/** API端点配置 */
const BASE = ''  // 同源代理

export default {
  // 笔记
  noteList: `${BASE}/note`,
  noteDetail: (id) => `${BASE}/note/${id}`,
  noteCreate: `${BASE}/note`,
  noteUpdate: (id) => `${BASE}/note/${id}`,
  noteDelete: (id) => `${BASE}/note/${id}`,
  noteSearch: (q) => `${BASE}/note/search/${encodeURIComponent(q)}`,

  // AI助手
  chatQuery: `${BASE}/chat/query`,
  chatSessions: `${BASE}/chat/sessions`,
  chatSession: (id) => `${BASE}/chat/sessions/${id}`,
  chatDeleteSession: (id) => `${BASE}/chat/sessions/${id}`,

  // 知识库
  knowledgeUpload: `${BASE}/knowledge/upload`,
  knowledgeDocuments: `${BASE}/knowledge/documents`,
  knowledgeChunks: (md5) => `${BASE}/knowledge/documents/${md5}/chunks`,
  knowledgeDelete: (md5) => `${BASE}/knowledge/documents/${md5}`,
  knowledgeClear: `${BASE}/knowledge/clear`,
}
