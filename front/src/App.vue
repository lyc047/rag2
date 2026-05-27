<template>
  <div id="app-container">
    <router-view />
    <!-- 底部导航栏 -->
    <van-tabbar v-model="active" route placeholder="bottom" safe-area-inset-bottom>
      <van-tabbar-item to="/notes">
        <template #icon="props">{{ props.active ? '📝' : '📝' }}</template>
        笔记
      </van-tabbar-item>
      <van-tabbar-item to="/chat">
        <template #icon="props">{{ props.active ? '🤖' : '🤖' }}</template>
        AI助手
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = ref(0)

// 根据路由同步底部导航激活项
watch(() => route.path, (path) => {
  if (path.startsWith('/notes')) active.value = 0
  else if (path.startsWith('/chat')) active.value = 1
}, { immediate: true })
</script>
