import { useState } from 'react'
import TextInput from '../components/TextInput'
import LanguageSelector from '../components/LanguageSelector'
import AudioPlayer from '../components/AudioPlayer'
import FavoriteButton from '../components/FavoriteButton'
import { speakText } from '../api/client'
import useAppStore from '../store/useAppStore'
import { useT } from '../hooks/useT'

function HomePage() {
  const {
    currentText, setCurrentText,
    currentLanguage,
    currentVoice,
    audioUrl, fromCache, setAudioUrl,
    isLoading, setIsLoading,
  } = useAppStore()
  const t = useT()

  const [error, setError] = useState('')

  const handleSpeak = async () => {
    if (!currentText.trim()) {
      setError(t('home.err.empty'))
      return
    }
    if (currentText.length > 1000) {
      setError(t('home.err.toolong'))
      return
    }

    setError('')
    setIsLoading(true)
    try {
      const { audioUrl: url, fromCache: cached } = await speakText(currentText, currentLanguage, currentVoice || undefined)
      setAudioUrl(url, cached)
    } catch (err) {
      console.error('TTS 合成失败:', err)
      if (err.response?.status === 429) {
        setError(t('home.err.ratelimit'))
      } else if (err.response?.status === 503) {
        setError(err.response?.data?.detail || t('home.err.unavailable'))
      } else {
        setError(err.response?.data?.detail || t('home.err.failed'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSpeak()
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8" onKeyDown={handleKeyDown}>
      {/* 页面标题 */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{t('home.title')}</h1>
        <p className="text-gray-500">{t('home.subtitle')}</p>
      </div>

      {/* 主卡片 */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-5">
        {/* 文字输入区域 */}
        <TextInput
          value={currentText}
          onChange={setCurrentText}
          disabled={isLoading}
        />

        {/* 语言选择 */}
        <LanguageSelector disabled={isLoading} />

        {/* 操作区：朗读按钮 + 收藏按钮 */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSpeak}
            disabled={isLoading || !currentText.trim() || currentText.length > 1000}
            className="btn-primary flex-1 flex items-center justify-center gap-2 py-3 text-base"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('home.speaking')}
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15.536 8.464a5 5 0 010 7.072M12 6v12m-4.536-9.536a5 5 0 000 7.072M5 12H3m1-7l3 3m10.95 8.95L19 19m0-14l-3 3" />
                </svg>
                {t('home.speak')}
                <span className="text-xs opacity-70 hidden sm:inline">{t('home.shortcut')}</span>
              </>
            )}
          </button>

          {/* 收藏按钮 */}
          <FavoriteButton text={currentText} language={currentLanguage} />
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-600 flex items-start gap-2">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}
      </div>

      {/* 音频播放器 */}
      <div className="mt-4">
        <AudioPlayer audioUrl={audioUrl} fromCache={fromCache} isLoading={isLoading} />
      </div>

      {/* 使用提示 */}
      {!audioUrl && !isLoading && (
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { icon: '✍️', titleKey: 'home.tip1.title', descKey: 'home.tip1.desc' },
            { icon: '🌐', titleKey: 'home.tip2.title', descKey: 'home.tip2.desc' },
            { icon: '🔊', titleKey: 'home.tip3.title', descKey: 'home.tip3.desc' },
          ].map((item) => (
            <div key={item.titleKey} className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <div className="text-2xl mb-2">{item.icon}</div>
              <div className="text-sm font-medium text-gray-700">{t(item.titleKey)}</div>
              <div className="text-xs text-gray-400 mt-0.5">{t(item.descKey)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HomePage
