import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createFavorite, getGroups } from '../api/client'
import useAppStore from '../store/useAppStore'

function FavoriteButton({ text, language }) {
  const isLoggedIn = useAppStore((s) => !!s.user && !!s.token)
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [groups, setGroups] = useState([])
  const [selectedGroupId, setSelectedGroupId] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  // 表单打开时加载分组列表
  useEffect(() => {
    if (showForm && isLoggedIn) {
      getGroups().then(setGroups).catch(() => {})
    }
  }, [showForm, isLoggedIn])

  const handleClick = () => {
    if (!isLoggedIn) {
      navigate('/login')
      return
    }
    if (!text.trim()) return
    setTitle(text.slice(0, 15).replace(/\n/g, ' '))
    setSelectedGroupId('')
    setShowForm(true)
    setSaved(false)
    setError('')
  }

  const handleSave = async () => {
    if (!title.trim()) {
      setError('请输入标题')
      return
    }
    setSaving(true)
    setError('')
    try {
      const groupId = selectedGroupId ? Number(selectedGroupId) : null
      await createFavorite(title.trim(), text, language, groupId)
      setSaved(true)
      setShowForm(false)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || '收藏失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={handleClick}
        disabled={!text.trim()}
        title={isLoggedIn ? '收藏这段文字' : '登录后可收藏'}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all
          ${saved
            ? 'bg-yellow-50 text-yellow-600 border border-yellow-300'
            : 'bg-white text-gray-600 border border-gray-300 hover:border-yellow-400 hover:text-yellow-500'
          }
          disabled:opacity-40 disabled:cursor-not-allowed`}
      >
        <svg
          className={`w-4 h-4 transition-transform ${saved ? 'scale-110 fill-yellow-400' : ''}`}
          fill={saved ? 'currentColor' : 'none'}
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
          />
        </svg>
        {saved ? '已收藏' : '收藏'}
      </button>

      {showForm && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setShowForm(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 bg-white rounded-xl shadow-lg border border-gray-200 p-4 w-72">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">收藏这段文字</h3>

            <p className="text-xs text-gray-500 bg-gray-50 rounded p-2 mb-3 line-clamp-2">
              {text.slice(0, 60)}{text.length > 60 ? '...' : ''}
            </p>

            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="给这条收藏起个名字"
              maxLength={50}
              className="input-base text-sm mb-3"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            />

            {/* 分组选择 */}
            <select
              value={selectedGroupId}
              onChange={(e) => setSelectedGroupId(e.target.value)}
              className="input-base text-sm mb-3"
            >
              <option value="">不归组（未分组）</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>

            {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

            <div className="flex gap-2">
              <button onClick={() => setShowForm(false)} className="btn-secondary text-sm flex-1">
                取消
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary text-sm flex-1">
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default FavoriteButton
