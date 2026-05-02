import { computed, ref } from 'vue'
import { createI18n } from 'vue-i18n'
import enUS from './locales/en-US'
import zhCN from './locales/zh-CN'
import elementZhCN from 'element-plus/es/locale/lang/zh-cn'
import elementEnUS from 'element-plus/es/locale/lang/en'

export const LOCALE_KEY = 'skillvault_locale'
export const DEFAULT_LOCALE = 'zh-CN'

const saved = localStorage.getItem(LOCALE_KEY)
const locale = ref(saved === 'en-US' || saved === 'zh-CN' ? saved : DEFAULT_LOCALE)

export const i18n = createI18n({
  legacy: false,
  locale: locale.value,
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export function setLocale(next: string) {
  const v = next === 'en-US' ? 'en-US' : 'zh-CN'
  locale.value = v
  i18n.global.locale.value = v
  localStorage.setItem(LOCALE_KEY, v)
}

export function getLocale() {
  return locale.value
}

export const elementLocale = computed(() => (locale.value === 'en-US' ? elementEnUS : elementZhCN))
