import { createPinia } from 'pinia'
import App from './App.vue'
import router from './lib/router'
import 'vfonts/Lato.css'
import 'vfonts/FiraCode.css'
import naive from './lib/plugins/naive-ui'
import GlobalProvider from './components/GlobalProvider.vue'
import { useThemeStore } from './lib/store/theme'

const app = createApp(App)
const pinia = createPinia()

app.use(naive)
app.use(pinia)
app.use(router)
app.component('GlobalProvider', GlobalProvider)

const themeStore = useThemeStore(pinia)
themeStore.init()

app.mount('#app') 