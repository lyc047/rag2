<template>
  <div class="chat-page">
    <van-nav-bar :title="t('aiAssistant')" fixed placeholder>
      <template #right>
        <span class="nav-action" @click="showSessions = true">{{ t('chatHistory') }}</span>
      </template>
    </van-nav-bar>

    <!-- 消息列表 -->
    <div class="message-list" ref="msgListRef">
      <!-- 欢迎语 -->
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon"><img src="/2.gif" class="robot-gif welcome-gif" /></div>
        <div class="welcome-text">{{ t('welcome') }}</div>
        <div class="welcome-sub">{{ t('welcomeSub') }}</div>
        <div class="quick-actions">
          <van-button v-for="q in quickQuestions" :key="q" size="small" round
            @click="sendQuick(q)">{{ q }}</van-button>
        </div>
      </div>

      <!-- 消息气泡 -->
      <div v-for="(msg, i) in messages" :key="i" class="msg-item" :class="msg.role">
        <div class="msg-avatar">
          <span v-if="msg.role === 'user'">👤</span>
          <img v-else src="/1.gif" class="robot-gif" />
        </div>
        <div class="msg-bubble">
          <div class="msg-text" v-html="renderContent(msg.content)"></div>
          <!-- 思考过程 -->
          <details v-if="msg.thinking" class="thinking-block">
            <summary>{{ t('thinking') }}</summary>
            <div class="thinking-content">{{ msg.thinking }}</div>
          </details>
          <!-- 工具调用 -->
          <div v-if="msg.toolCalls" class="tool-calls">
            <div v-for="tc in msg.toolCalls" :key="tc.tool" class="tool-tag">
              🔧 {{ tc.tool }}
            </div>
          </div>
        </div>
      </div>

      <!-- 流式输出中的消息 -->
      <div v-if="streaming" class="msg-item assistant">
        <div class="msg-avatar"><img src="/1.gif" class="robot-gif" /></div>
        <div class="msg-bubble">
          <div class="msg-text" v-html="renderContent(streamingContent)"></div>
          <img src="/3.gif" class="thinking-gif" />
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="input-bar">
      <input v-model="input" :placeholder="t('inputPlaceholder')" class="chat-input"
        @keyup.enter="send" :disabled="streaming" />
      <van-button size="small" type="primary" round :loading="streaming"
        @click="send">{{ t('send') }}</van-button>
    </div>

    <!-- 会话列表弹窗 -->
    <van-popup v-model:show="showSessions" position="right" :style="{ width: '80%', height: '100%' }">
      <div class="session-panel">
        <van-nav-bar :title="t('chatHistory')" :left-text="t('close')" @click-left="showSessions = false" />
        <van-button block round type="primary" @click="newSession" style="margin:12px 16px">{{ t('newSession') }}</van-button>
        <div v-for="s in sessions" :key="s.id" class="session-item"
          @click="switchSession(s.id)">
          <div class="session-title">{{ s.title }}</div>
          <div class="session-time">{{ formatDate(s.updated_at) }}</div>
          <van-icon name="delete-o" @click.stop="deleteSession(s.id)" />
        </div>
        <van-empty v-if="sessions.length === 0" :description="t('noSessions')" />
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import axios from 'axios'
import API from '../config/api.js'
import { useI18n } from '../composables/useI18n.js'

const { t, currentLang } = useI18n()

const route = useRoute()
const messages = ref([])
const sessions = ref([])
const input = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const currentSessionId = ref(null)
const showSessions = ref(false)
const msgListRef = ref(null)
const thinkingBlocks = ref([])

const quickQuestions = computed(() => [
  t('quick1'), t('quick2'), t('quick3')
])

// 初始化
onMounted(async () => {
  await loadSessions()
  const sid = route.params.sessionId
  if (sid) { await switchSession(sid) }
})

// 加载会话列表
async function loadSessions() {
  try {
    const { data } = await axios.get(API.chatSessions)
    if (data.code === 200) sessions.value = data.data || []
  } catch (e) { /* */ }
}

// 切换会话
async function switchSession(sid) {
  showSessions.value = false
  currentSessionId.value = sid
  try {
    const { data } = await axios.get(API.chatSession(sid))
    if (data.code === 200 && data.data) {
      messages.value = data.data.messages.map(m => ({
        role: m.role, content: m.content, thinking: '', toolCalls: []
      }))
      scrollBottom()
    }
  } catch (e) { showToast(t('loadSessionFail')) }
}

// 发送消息
async function send() {
  const query = input.value.trim()
  if (!query || streaming.value) return
  input.value = ''

  messages.value.push({ role: 'user', content: query, thinking: '', toolCalls: [] })
  streaming.value = true
  streamingContent.value = ''
  scrollBottom()

  try {
    const resp = await fetch(API.chatQuery, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: currentSessionId.value, lang: currentLang.value }),
    })

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let thinkingText = ''
    let toolCalls = []

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
          if (evt.type === 'token') {
            streamingContent.value += evt.content
            scrollBottom()
          } else if (evt.type === 'tool_start') {
            toolCalls.push({ tool: evt.tool })
            thinkingText += `\n🔧 调用工具: ${evt.tool}\n`
          } else if (evt.type === 'tool_end') {
            thinkingText += `📋 结果: ${evt.output}\n`
          } else if (evt.type === 'finish') {
            if (!currentSessionId.value) currentSessionId.value = evt.session_id
          }
        } catch (e) { /* */ }
      }
    }

    // 保存助手消息
    if (streamingContent.value) {
      messages.value.push({
        role: 'assistant', content: streamingContent.value,
        thinking: thinkingText, toolCalls: toolCalls
      })
    }
    if (currentSessionId.value) await loadSessions()
  } catch (e) {
    showToast(t('requestFail'))
  } finally {
    streaming.value = false
    streamingContent.value = ''
  }
}

function sendQuick(q) { input.value = q; send() }
async function newSession() {
  showSessions.value = false
  currentSessionId.value = null
  messages.value = []
}
async function deleteSession(sid) {
  try {
    await showConfirmDialog({ title: t('deleteConfirm'), message: t('confirmDeleteSession') })
    await axios.delete(API.chatDeleteSession(sid))
    await loadSessions()
  } catch (e) { /* 取消或失败 */ }
}
function scrollBottom() {
  nextTick(() => {
    const el = msgListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '' }
function renderContent(text) {
  if (!text) return ''
  return text.replace(/\n/g, '<br>').replace(/`([^`]+)`/g, '<code>$1</code>')
}
</script>

<style scoped>
.nav-action { font-size: 14px; color: var(--color-primary); cursor: pointer; }
.message-list { padding: 8px 12px 100px; overflow-y: auto; height: calc(100vh - 100px); }
.welcome { text-align: center; padding: 60px 20px; }
.welcome-icon { margin-bottom: 12px; }
.robot-gif { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
.welcome-gif { width: 72px; height: 72px; }
.welcome-text { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
.welcome-sub { color: var(--color-text-light); font-size: 13px; margin-bottom: 20px; }
.quick-actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }

.msg-item { display: flex; margin-bottom: 16px; gap: 8px; }
.msg-item.user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--color-surface);
  display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.msg-bubble { max-width: 75%; background: var(--color-card); border-radius: var(--radius);
  padding: 10px 14px; box-shadow: var(--color-shadow); }
.msg-item.user .msg-bubble { background: var(--color-primary-light); }
.msg-text { font-size: 14px; line-height: 1.6; word-break: break-word; }
.msg-text :deep(code) { background: rgba(0,0,0,0.06); padding: 1px 4px; border-radius: 4px;
  font-size: 13px; }

.thinking-block { margin-top: 8px; font-size: 12px; }
.thinking-block summary { color: var(--color-text-light); cursor: pointer; }
.thinking-content { color: var(--color-text-light); padding: 6px 0; font-size: 12px; white-space: pre-wrap; }
.tool-calls { margin-top: 6px; display: flex; gap: 4px; flex-wrap: wrap; }
.tool-tag { font-size: 11px; background: var(--color-surface); padding: 2px 8px; border-radius: 10px; }

.thinking-gif { width: 20px; height: 20px; margin-left: 4px; vertical-align: middle; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.input-bar { position: fixed; bottom: 50px; left: 0; right: 0; max-width: 750px; margin: 0 auto;
  display: flex; gap: 8px; padding: 10px 12px; background: var(--color-card); border-top: 1px solid var(--color-border);
  align-items: center; z-index: 100; }
.chat-input { flex: 1; border: 1px solid var(--color-border); border-radius: 20px; padding: 8px 16px;
  font-size: 14px; outline: none; background: var(--color-bg); font-family: inherit; }

.session-panel { height: 100%; overflow-y: auto; }
.session-item { display: flex; align-items: center; padding: 14px 16px;
  border-bottom: 1px solid var(--color-border); cursor: pointer; gap: 8px; }
.session-item:active { background: var(--color-surface); }
.session-title { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-time { font-size: 11px; color: var(--color-text-light); flex-shrink: 0; }
</style>
