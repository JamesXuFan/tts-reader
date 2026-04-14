import { useEffect } from 'react'
import { getLanguages } from '../api/client'
import useAppStore from '../store/useAppStore'

// ============================================================
// LanguageSelector — 语言和声音选择器
// ============================================================
// 数据结构说明（来自后端 /api/v1/tts/languages）：
// [
//   {
//     language_code: "zh-CN",
//     language_name: "普通话（中国大陆）",
//     voices: [
//       { name: "zh-CN-Standard-A", gender: "FEMALE", description: "标准女声" },
//       ...
//     ]
//   },
//   ...
// ]
// ============================================================

function LanguageSelector({ disabled = false }) {
  const { languages, setLanguages, currentLanguage, setCurrentLanguage, currentVoice, setCurrentVoice } = useAppStore()

  // 组件挂载时从后端加载语言列表（只加载一次）
  useEffect(() => {
    if (languages.length === 0) {
      getLanguages()
        .then((data) => {
          setLanguages(data)
          // 如果当前没有选择语言，默认选第一个
          if (data.length > 0 && !currentLanguage) {
            setCurrentLanguage(data[0].code)
          }
        })
        .catch((err) => {
          console.error('加载语言列表失败:', err)
        })
    }
  }, [])

  // 找到当前选中语言的声音列表
  // 后端返回的 voices 是字符串数组，如 ["kore", "charon"]
  const currentLangData = languages.find((l) => l.code === currentLanguage)
  const voices = currentLangData?.voices ?? []

  const handleLanguageChange = (langCode) => {
    setCurrentLanguage(langCode)
    setCurrentVoice('')
  }

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {/* 语言选择 */}
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          选择语言
        </label>
        <select
          value={currentLanguage}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={disabled || languages.length === 0}
          className="input-base cursor-pointer"
        >
          {languages.length === 0 ? (
            <option value="">加载中...</option>
          ) : (
            languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* 声音选择（只有当前语言有多个声音时才显示） */}
      {voices.length > 1 && (
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            选择声音
          </label>
          <select
            value={currentVoice}
            onChange={(e) => setCurrentVoice(e.target.value)}
            disabled={disabled}
            className="input-base cursor-pointer"
          >
            <option value="">默认声音</option>
            {voices.map((voice) => (
              <option key={voice} value={voice}>
                {voice}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

export default LanguageSelector
