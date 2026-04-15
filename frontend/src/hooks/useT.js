import useAppStore from '../store/useAppStore'
import { translations } from '../locales/translations'

// ============================================================
// useT — i18n 翻译 hook
// ============================================================
// 用法：
//   const t = useT()
//   t('nav.home')              → "首页" 或 "Home"
//   t('favorites.playCount', 5) → "播放 5 次" 或 "Played 5 times"
// ============================================================

export function useT() {
  const lang = useAppStore((s) => s.uiLang)
  return (key, ...args) => {
    const str = translations[lang]?.[key] ?? translations['zh']?.[key] ?? key
    if (args.length === 0) return str
    // 替换 {0}, {1}, ... 占位符
    return str.replace(/\{(\d+)\}/g, (_, i) => args[Number(i)] ?? '')
  }
}
