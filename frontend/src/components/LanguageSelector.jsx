import { useEffect } from 'react'
import { getLanguages } from '../api/client'
import useAppStore from '../store/useAppStore'
import { useT } from '../hooks/useT'

function LanguageSelector({ disabled = false }) {
  const { languages, setLanguages, currentLanguage, setCurrentLanguage, currentVoice, setCurrentVoice } = useAppStore()
  const t = useT()

  useEffect(() => {
    if (languages.length === 0) {
      getLanguages()
        .then((data) => {
          setLanguages(data)
          if (data.length > 0 && !currentLanguage) {
            setCurrentLanguage(data[0].code)
          }
        })
        .catch((err) => {
          console.error('加载语言列表失败:', err)
        })
    }
  }, [])

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
          {t('lang.selectLang')}
        </label>
        <select
          value={currentLanguage}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={disabled || languages.length === 0}
          className="input-base cursor-pointer"
        >
          {languages.length === 0 ? (
            <option value="">{t('common.loading')}</option>
          ) : (
            languages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {t('lang.' + lang.code) || lang.name}
              </option>
            ))
          )}
        </select>
      </div>

      {/* 声音选择 */}
      {voices.length > 1 && (
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            {t('lang.selectVoice')}
          </label>
          <select
            value={currentVoice}
            onChange={(e) => setCurrentVoice(e.target.value)}
            disabled={disabled}
            className="input-base cursor-pointer"
          >
            <option value="">{t('lang.defaultVoice')}</option>
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
