import { useRef, useState, useEffect } from 'react'
import { useT } from '../hooks/useT'

function AudioPlayer({ audioUrl, fromCache = false, isLoading }) {
  const t = useT()
  const audioRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playbackRate, setPlaybackRate] = useState(1)

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
    if (audioUrl && audioRef.current) {
      audioRef.current.load()
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {})
    }
  }, [audioUrl])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate
    }
  }, [playbackRate])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (e) => {
    const newTime = Number(e.target.value)
    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00'
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  const speedOptions = [0.5, 0.75, 1, 1.25, 1.5, 2]

  if (isLoading) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
        <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-blue-700">{t('player.generating')}</p>
          <p className="text-xs text-blue-500 mt-0.5">{t('player.generatingDesc')}</p>
        </div>
      </div>
    )
  }

  if (!audioUrl) {
    return (
      <div className="bg-gray-50 border border-dashed border-gray-300 rounded-xl p-6 text-center text-gray-400 text-sm">
        {t('player.empty')}
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDuration(audioRef.current?.duration ?? 0)}
        onEnded={() => setIsPlaying(false)}
        className="hidden"
      />

      <div className="flex items-center gap-3">
        {/* 播放/暂停按钮 */}
        <button
          onClick={togglePlay}
          className="w-10 h-10 rounded-full bg-primary-500 hover:bg-primary-600 active:bg-primary-700 text-white flex items-center justify-center flex-shrink-0 transition-colors shadow-md"
        >
          {isPlaying ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* 进度条 */}
        <div className="flex-1 min-w-0">
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-1.5 accent-primary-500 cursor-pointer"
          />
          <div className="flex justify-between text-xs text-blue-400 mt-0.5">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* 播放速度 */}
        <select
          value={playbackRate}
          onChange={(e) => setPlaybackRate(Number(e.target.value))}
          className="text-xs text-blue-600 bg-transparent border border-blue-200 rounded px-1.5 py-0.5 cursor-pointer flex-shrink-0"
          title={t('player.speed')}
        >
          {speedOptions.map((r) => (
            <option key={r} value={r}>{r}x</option>
          ))}
        </select>

        {/* 缓存标签 */}
        {fromCache && (
          <span
            className="text-xs text-green-600 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded flex-shrink-0"
            title={t('player.cached')}
          >
            {t('player.cached')}
          </span>
        )}

        {/* 下载按钮 */}
        <a
          href={audioUrl}
          download="dictation-audio.mp3"
          className="text-blue-400 hover:text-blue-600 transition-colors flex-shrink-0"
          title={t('player.download')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </a>
      </div>
    </div>
  )
}

export default AudioPlayer
