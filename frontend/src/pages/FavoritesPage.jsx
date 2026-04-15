import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  getGroups, createGroup, deleteGroup,
  getFavorites, updateFavorite, deleteFavorite, speakFavorite,
} from '../api/client'
import useAppStore from '../store/useAppStore'
import AudioPlayer from '../components/AudioPlayer'
import { useToast, ToastContainer } from '../components/Toast'
import { useT } from '../hooks/useT'

const PRESET_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
]

function FavoritesPage() {
  const navigate = useNavigate()
  const isLoggedIn = useAppStore((s) => !!s.user && !!s.token)
  const hasHydrated = useAppStore((s) => s._hasHydrated)
  const setCurrentText = useAppStore((s) => s.setCurrentText)
  const setCurrentLanguage = useAppStore((s) => s.setCurrentLanguage)
  const setFavoritesCount = useAppStore((s) => s.setFavoritesCount)
  const { toasts, showToast } = useToast()
  const t = useT()

  const [groups, setGroups] = useState([])
  const [selectedGroupId, setSelectedGroupId] = useState(null)

  const [favorites, setFavorites] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const searchTimerRef = useRef(null)
  const [loadingFavs, setLoadingFavs] = useState(false)

  const [showGroupForm, setShowGroupForm] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupColor, setNewGroupColor] = useState(PRESET_COLORS[0])
  const [creatingGroup, setCreatingGroup] = useState(false)

  const [playingUrl, setPlayingUrl] = useState(null)
  const [playingId, setPlayingId] = useState(null)
  const [loadingPlayId, setLoadingPlayId] = useState(null)

  useEffect(() => {
    if (hasHydrated && !isLoggedIn) {
      navigate('/login')
    }
  }, [hasHydrated, isLoggedIn])

  const loadGroups = useCallback(async () => {
    try {
      const data = await getGroups()
      setGroups(data)
    } catch (err) {
      console.error('加载分组失败:', err)
    }
  }, [])

  const loadFavorites = useCallback(async () => {
    setLoadingFavs(true)
    try {
      const data = await getFavorites({
        groupId: selectedGroupId,
        search: search || undefined,
        page,
        pageSize: 10,
      })
      setFavorites(data.items)
      setTotal(data.total)
      if (selectedGroupId === null && !search) setFavoritesCount(data.total)
    } catch (err) {
      console.error('加载收藏失败:', err)
    } finally {
      setLoadingFavs(false)
    }
  }, [selectedGroupId, search, page])

  useEffect(() => { loadGroups() }, [loadGroups])
  useEffect(() => { loadFavorites() }, [loadFavorites])

  const handleSelectGroup = (id) => {
    setSelectedGroupId(id)
    setPage(1)
  }

  const handleSearchInput = (val) => {
    setSearchInput(val)
    clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      setSearch(val)
      setPage(1)
    }, 400)
  }

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) return
    setCreatingGroup(true)
    try {
      await createGroup(newGroupName.trim(), newGroupColor)
      setNewGroupName('')
      setShowGroupForm(false)
      await loadGroups()
      showToast(t('favorites.toast.created'))
    } catch (err) {
      showToast(err.response?.data?.detail || t('favorites.toast.groupDeleteFailed'), 'error')
    } finally {
      setCreatingGroup(false)
    }
  }

  const handleDeleteGroup = async (group) => {
    if (!window.confirm(t('favorites.confirm.deleteGroup', group.name))) return
    try {
      await deleteGroup(group.id)
      if (selectedGroupId === group.id) setSelectedGroupId(null)
      await loadGroups()
      await loadFavorites()
      showToast(t('favorites.toast.groupDeleted'))
    } catch (err) {
      showToast(t('favorites.toast.groupDeleteFailed'), 'error')
    }
  }

  const handleMoveGroup = async (fav, groupId) => {
    try {
      await updateFavorite(fav.id, { group_id: groupId })
      await loadFavorites()
      await loadGroups()
      showToast(t('favorites.toast.groupMoved'))
    } catch (err) {
      showToast(err.response?.data?.detail || t('favorites.toast.groupMoveFailed'), 'error')
    }
  }

  const handleDeleteFavorite = async (fav) => {
    if (!window.confirm(t('favorites.confirm.deleteFav', fav.title))) return
    try {
      await deleteFavorite(fav.id)
      await loadFavorites()
      await loadGroups()
      showToast(t('favorites.toast.favDeleted'))
    } catch (err) {
      showToast(t('favorites.toast.favDeleteFailed'), 'error')
    }
  }

  const handlePlayFavorite = async (fav) => {
    setLoadingPlayId(fav.id)
    try {
      const url = await speakFavorite(fav.id)
      setPlayingUrl(url)
      setPlayingId(fav.id)
    } catch (err) {
      showToast(t('favorites.toast.playFailed'), 'error')
    } finally {
      setLoadingPlayId(null)
    }
  }

  const handleEditInHome = (fav) => {
    setCurrentText(fav.text_content)
    setCurrentLanguage(fav.language)
    navigate('/')
  }

  const totalPages = Math.ceil(total / 10)

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <ToastContainer toasts={toasts} />
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t('favorites.title')}</h1>

      <div className="flex gap-5">
        {/* ---- 左侧：分组侧边栏 ---- */}
        <aside className="w-44 flex-shrink-0 hidden sm:block">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-3 py-2.5 border-b border-gray-100 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t('favorites.groups')}</span>
              <button
                onClick={() => setShowGroupForm(!showGroupForm)}
                className="text-gray-400 hover:text-primary-500 transition-colors"
                title={t('favorites.newGroup')}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>

            {showGroupForm && (
              <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder={t('favorites.groupNamePlaceholder')}
                  maxLength={20}
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
                  className="input-base text-xs py-1.5 mb-2"
                />
                <div className="flex flex-wrap gap-1 mb-2">
                  {PRESET_COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={() => setNewGroupColor(c)}
                      className={`w-5 h-5 rounded-full transition-transform ${newGroupColor === c ? 'scale-125 ring-2 ring-offset-1 ring-gray-400' : ''}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
                <button
                  onClick={handleCreateGroup}
                  disabled={creatingGroup || !newGroupName.trim()}
                  className="btn-primary w-full text-xs py-1"
                >
                  {creatingGroup ? t('common.creating') : t('common.create')}
                </button>
              </div>
            )}

            <GroupItem
              label={t('favorites.all')}
              count={groups.reduce((s, g) => s + (g.favorites_count ?? 0), 0)}
              active={selectedGroupId === null}
              onClick={() => handleSelectGroup(null)}
            />

            <GroupItem
              label={t('common.ungrouped')}
              count={null}
              active={selectedGroupId === 0}
              onClick={() => handleSelectGroup(0)}
            />

            {groups.map((g) => (
              <GroupItem
                key={g.id}
                label={g.name}
                count={g.favorites_count}
                active={selectedGroupId === g.id}
                color={g.color}
                onClick={() => handleSelectGroup(g.id)}
                onDelete={() => handleDeleteGroup(g)}
              />
            ))}
          </div>
        </aside>

        {/* ---- 右侧：收藏列表 ---- */}
        <div className="flex-1 min-w-0">
          {/* 手机端分组标签 */}
          <div className="sm:hidden flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-hide">
            <MobileGroupTag label={t('favorites.all')} active={selectedGroupId === null} onClick={() => handleSelectGroup(null)} />
            <MobileGroupTag label={t('common.ungrouped')} active={selectedGroupId === 0} onClick={() => handleSelectGroup(0)} />
            {groups.map((g) => (
              <MobileGroupTag key={g.id} label={g.name} color={g.color} active={selectedGroupId === g.id} onClick={() => handleSelectGroup(g.id)} />
            ))}
          </div>

          {/* 搜索框 */}
          <div className="mb-4">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchInput(e.target.value)}
              placeholder={t('favorites.search')}
              className="input-base"
            />
          </div>

          {/* 正在播放的音频 */}
          {playingUrl && (
            <div className="mb-4">
              <AudioPlayer audioUrl={playingUrl} isLoading={false} />
            </div>
          )}

          {/* 收藏卡片列表 */}
          {loadingFavs ? (
            <div className="text-center py-12 text-gray-400">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-primary-500 rounded-full animate-spin mx-auto mb-2" />
              {t('common.loading')}
            </div>
          ) : favorites.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-4xl mb-3">{search ? '🔍' : '📭'}</div>
              {search ? (
                <p className="text-sm">
                  {t('favorites.noResult')} "<span className="font-medium text-gray-600">{search}</span>"{t('favorites.noResultSuffix')}
                </p>
              ) : (
                <>
                  <p className="text-sm mb-4">{t('favorites.empty')}</p>
                  <Link to="/" className="btn-primary text-sm inline-block">{t('favorites.goHome')}</Link>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {favorites.map((fav) => (
                <FavoriteCard
                  key={fav.id}
                  fav={fav}
                  groups={groups}
                  isPlayingThis={playingId === fav.id}
                  isLoadingThis={loadingPlayId === fav.id}
                  onPlay={() => handlePlayFavorite(fav)}
                  onEdit={() => handleEditInHome(fav)}
                  onDelete={() => handleDeleteFavorite(fav)}
                  onMoveGroup={(groupId) => handleMoveGroup(fav, groupId)}
                  t={t}
                />
              ))}
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary px-3 py-1.5 text-sm disabled:opacity-40"
              >
                {t('common.prev')}
              </button>
              <span className="text-sm text-gray-500">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary px-3 py-1.5 text-sm disabled:opacity-40"
              >
                {t('common.next')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function GroupItem({ label, count, active, color, onClick, onDelete }) {
  return (
    <div
      className={`group flex items-center px-3 py-2 cursor-pointer text-sm transition-colors ${
        active ? 'bg-primary-50 text-primary-600 font-medium' : 'text-gray-600 hover:bg-gray-50'
      }`}
      onClick={onClick}
    >
      {color ? (
        <span className="w-2 h-2 rounded-full mr-2 flex-shrink-0" style={{ backgroundColor: color }} />
      ) : (
        <span className="w-2 h-2 mr-2 flex-shrink-0" />
      )}
      <span className="flex-1 truncate">{label}</span>
      {count != null && (
        <span className="text-xs text-gray-400 ml-1">{count}</span>
      )}
      {onDelete && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="hidden group-hover:block text-gray-300 hover:text-red-400 ml-1 transition-colors"
          title="Delete group"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}

function MobileGroupTag({ label, color, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex-shrink-0 flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors ${
        active ? 'bg-primary-500 text-white' : 'bg-white text-gray-600 border border-gray-300'
      }`}
    >
      {color && <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />}
      {label}
    </button>
  )
}

function FavoriteCard({ fav, groups, isPlayingThis, isLoadingThis, onPlay, onEdit, onDelete, onMoveGroup, t }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = fav.text_content?.length > 100

  return (
    <div className={`bg-white rounded-xl border ${isPlayingThis ? 'border-primary-300 shadow-md' : 'border-gray-200'} p-4 transition-shadow hover:shadow-sm`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {fav.group_color && (
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: fav.group_color }} />
            )}
            <h3 className="font-medium text-gray-800 truncate">{fav.title}</h3>
          </div>
          <p className={`text-sm text-gray-500 leading-relaxed ${!expanded && isLong ? 'line-clamp-2' : ''}`}>
            {fav.text_content}
          </p>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-primary-500 mt-1 hover:underline"
            >
              {expanded ? t('favorites.collapse') : t('favorites.expand')}
            </button>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 flex-wrap">
            <span>{fav.language}</span>
            {fav.play_count > 0 && <span>{t('favorites.playCount', fav.play_count)}</span>}
            <select
              value={fav.group_id ?? ''}
              onChange={(e) => onMoveGroup(e.target.value === '' ? 0 : Number(e.target.value))}
              onClick={(e) => e.stopPropagation()}
              className="text-xs border border-gray-200 rounded px-1.5 py-0.5 bg-white text-gray-500 cursor-pointer hover:border-primary-400 focus:outline-none focus:border-primary-400"
            >
              <option value="">{t('common.ungrouped')}</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            onClick={onPlay}
            disabled={isLoadingThis}
            title={t('favorites.playBtn')}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
              isPlayingThis
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 text-gray-500 hover:bg-primary-100 hover:text-primary-500'
            }`}
          >
            {isLoadingThis ? (
              <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          <button
            onClick={onEdit}
            title={t('favorites.editBtn')}
            className="w-8 h-8 rounded-full bg-gray-100 text-gray-500 hover:bg-blue-100 hover:text-blue-500 flex items-center justify-center transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>

          <button
            onClick={onDelete}
            title={t('favorites.deleteBtn')}
            className="w-8 h-8 rounded-full bg-gray-100 text-gray-500 hover:bg-red-100 hover:text-red-500 flex items-center justify-center transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

export default FavoritesPage
