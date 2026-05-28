<template>
  <div class="profile-page">
    <van-nav-bar :title="t('profile')" fixed placeholder />

    <div class="profile-content">
      <!-- 个性化 -->
      <van-cell-group :title="t('personalization')">
        <van-cell :title="t('language')" is-link @click="showLang = true">
          <template #default>
            <span class="cell-value">{{ currentLang === 'zh-CN' ? t('simplifiedChinese') : t('english') }}</span>
          </template>
        </van-cell>
        <van-cell :title="t('theme')" is-link @click="showTheme = true">
          <template #default>
            <span class="cell-value">{{ isDark ? t('darkMode') : t('lightMode') }}</span>
          </template>
        </van-cell>
        <van-cell :title="t('myKnowledge')" is-link @click="$router.push('/knowledge')" />
      </van-cell-group>

      <!-- 关于我们 -->
      <van-cell-group :title="t('aboutUs')">
        <div class="about-card card">
          <div class="about-icon">📝</div>
          <h3>{{ t('aboutTitle') }}</h3>
          <p>{{ t('aboutDesc') }}</p>
          <span class="about-version">{{ t('aboutVersion') }}</span>
        </div>
      </van-cell-group>
    </div>

    <!-- 语言选择弹窗 -->
    <van-popup v-model:show="showLang" position="bottom" round :style="{ padding: '20px' }">
      <h4 class="popup-title">{{ t('language') }}</h4>
      <van-cell v-for="opt in langOptions" :key="opt.value" :title="opt.label"
        :class="{ active: currentLang === opt.value }"
        @click="selectLang(opt.value)">
        <template #right-icon>
          <van-icon v-if="currentLang === opt.value" name="success" color="var(--color-primary)" />
        </template>
      </van-cell>
    </van-popup>

    <!-- 主题选择弹窗 -->
    <van-popup v-model:show="showTheme" position="bottom" round :style="{ padding: '20px' }">
      <h4 class="popup-title">{{ t('theme') }}</h4>
      <van-cell v-for="opt in themeOptions" :key="opt.value" :title="opt.label"
        @click="selectTheme(opt.value)">
        <template #right-icon>
          <van-icon v-if="currentTheme === opt.value" name="success" color="var(--color-primary)" />
        </template>
      </van-cell>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { showToast } from 'vant'
import { useI18n } from '../composables/useI18n.js'
import { useTheme } from '../composables/useTheme.js'

const { t, setLang, currentLang } = useI18n()
const { isDark, toggleTheme, getTheme } = useTheme()

const showLang = ref(false)
const showTheme = ref(false)

const currentTheme = ref(getTheme())

const langOptions = computed(() => [
  { label: t('simplifiedChinese'), value: 'zh-CN' },
  { label: t('english'), value: 'en' },
])

const themeOptions = computed(() => [
  { label: t('lightMode'), value: 'light' },
  { label: t('darkMode'), value: 'dark' },
])

function selectLang(lang) {
  setLang(lang)
  showLang.value = false
  showToast(t('langSwitched'))
}

function selectTheme(mode) {
  toggleTheme(mode)
  currentTheme.value = mode
  showTheme.value = false
  showToast(mode === 'dark' ? t('darkSwitched') : t('lightSwitched'))
}
</script>

<style scoped>
.profile-content { padding-top: 8px; background: var(--color-bg); min-height: 100vh; }
.cell-value { color: var(--color-text-light); font-size: 13px; }
.about-card { text-align: center; padding: 24px 16px; background: var(--color-card); }
.about-icon { font-size: 40px; margin-bottom: 12px; }
.about-card h3 { font-size: 18px; margin-bottom: 8px; color: var(--color-text); }
.about-card p { font-size: 13px; color: var(--color-text-light); line-height: 1.6; margin-bottom: 12px; }
.about-version { font-size: 11px; color: var(--color-text-lighter); }
.popup-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; padding: 0 16px; color: var(--color-text); }
.van-cell { cursor: pointer; background: var(--color-card) !important; }
.van-cell.active { background: var(--color-surface) !important; border-radius: var(--radius); }
:deep(.van-cell-group) { background: transparent !important; }
:deep(.van-cell-group__title) { color: var(--color-text-lighter) !important; }
</style>
