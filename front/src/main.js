import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from './App.vue'
import routes from './router/index.js'
import './style.css'

const app = createApp(App)

// Vue Router
const router = createRouter({ history: createWebHashHistory(), routes })
app.use(router)

// Pinia
app.use(createPinia())

// Vant组件按需引入（全局注册常用组件）
import {
  Button, Cell, CellGroup, Icon, NavBar, Tabbar, TabbarItem,
  Uploader, Progress, Dialog, Toast, Field, Form, Popup,
  Search, PullRefresh, List, Tag, Divider, Empty, Loading,
  ActionSheet, SwipeCell, Image, ImagePreview
} from 'vant'
import 'vant/lib/index.css'

const vantComponents = [
  Button, Cell, CellGroup, Icon, NavBar, Tabbar, TabbarItem,
  Uploader, Progress, Dialog, Toast, Field, Form, Popup,
  Search, PullRefresh, List, Tag, Divider, Empty, Loading,
  ActionSheet, SwipeCell, Image, ImagePreview
]
vantComponents.forEach(c => app.use(c))

app.mount('#app')
