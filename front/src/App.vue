<template>
  <div id="app-container">
    <router-view v-slot="{ Component, route }">
      <keep-alive :include="['AIChat']">
        <component :is="Component" :key="route.name" />
      </keep-alive>
    </router-view>
    <!-- 底部导航栏 -->
    <van-tabbar v-model="active" route placeholder="bottom" safe-area-inset-bottom>
      <van-tabbar-item to="/notes">
        <template #icon="props">{{ props.active ? '📝' : '📝' }}</template>
        {{ t('notes') }}
      </van-tabbar-item>
      <van-tabbar-item to="/chat">
        <template #icon="props">{{ props.active ? '🤖' : '🤖' }}</template>
        {{ t('aiAssistant') }}
      </van-tabbar-item>
      <van-tabbar-item to="/profile">
        <template #icon="props">{{ props.active ? '👤' : '👤' }}</template>
        {{ t('profile') }}
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from './composables/useI18n.js'

const route = useRoute()
const active = ref(0)
const { t } = useI18n()

// 根据路由同步底部导航激活项
watch(() => route.path, (path) => {
  if (path.startsWith('/notes')) active.value = 0
  else if (path.startsWith('/chat')) active.value = 1
  else if (path.startsWith('/profile')) active.value = 2
}, { immediate: true })
</script>
