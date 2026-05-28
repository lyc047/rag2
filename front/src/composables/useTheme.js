import { ref } from 'vue'

const THEME_KEY = 'rag2_theme'

const themes = {
  light: {
    bg: '#FAF7F2',
    surface: '#F5F0E8',
    card: '#FFFFFF',
    text: '#3D3226',
    textLight: '#6B5F4F',
    textLighter: '#8B7E6F',
    textLightest: '#ADA296',
    primary: '#D4914A',
    primaryLight: '#F0D9BC',
    border: '#E5DDD0',
    borderLight: '#F0EBE1',
    divider: '#EDE6DA',
    shadow: 'rgba(139, 126, 111, 0.12)',
    success: '#6B9E7A',
    danger: '#C4675C',
  },
  dark: {
    bg: '#1C1916',
    surface: '#2C2722',
    card: '#3C352E',
    text: '#EDE8E0',
    textLight: '#DDD5CB',
    textLighter: '#CDC3B6',
    textLightest: '#BAAEA1',
    primary: '#D4914A',
    primaryLight: '#3D3226',
    border: '#4A4037',
    borderLight: '#3C342D',
    divider: '#352E28',
    shadow: 'rgba(0, 0, 0, 0.40)',
    success: '#5A9E6F',
    danger: '#C4675C',
  },
}

const isDark = ref(localStorage.getItem(THEME_KEY) === 'dark')

function applyTheme() {
  const t = themes[isDark.value ? 'dark' : 'light']
  const root = document.documentElement
  root.style.setProperty('--color-bg', t.bg)
  root.style.setProperty('--color-surface', t.surface)
  root.style.setProperty('--color-card', t.card)
  root.style.setProperty('--color-text', t.text)
  root.style.setProperty('--color-text-light', t.textLight)
  root.style.setProperty('--color-text-lighter', t.textLighter)
  root.style.setProperty('--color-text-lightest', t.textLightest)
  root.style.setProperty('--color-primary', t.primary)
  root.style.setProperty('--color-primary-light', t.primaryLight)
  root.style.setProperty('--color-border', t.border)
  root.style.setProperty('--color-border-light', t.borderLight)
  root.style.setProperty('--color-divider', t.divider)
  root.style.setProperty('--color-shadow', t.shadow)
  root.style.setProperty('--color-success', t.success)
  root.style.setProperty('--color-danger', t.danger)
  root.style.setProperty('--van-tabbar-item-active-color', t.primary)
}

// 初始化时立即应用
applyTheme()

export function useTheme() {
  function toggleTheme(mode) {
    isDark.value = mode === 'dark'
    localStorage.setItem(THEME_KEY, mode)
    applyTheme()
  }

  function getTheme() {
    return isDark.value ? 'dark' : 'light'
  }

  return { isDark, toggleTheme, getTheme }
}
