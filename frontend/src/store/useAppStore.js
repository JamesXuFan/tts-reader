import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ============================================================
// Zustand 全局状态管理
// ============================================================

const useAppStore = create(
  persist(
    (set, get) => ({
      // ---- 用户状态 ----
      user: null,           // 当前登录用户信息，null 表示未登录
      token: null,          // JWT token

      // persist 恢复数据是异步的，_hasHydrated 标记恢复是否完成
      // 未完成前不能根据 user/token 做跳转判断，否则会误跳到登录页
      _hasHydrated: false,
      setHasHydrated: (val) => set({ _hasHydrated: val }),

      // 登录：保存用户信息和 token
      setUser: (user, token) => {
        localStorage.setItem('access_token', token)   // 同步到 localStorage（axios 拦截器用）
        set({ user, token })
      },

      // 登出：清除所有用户相关状态
      logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null, token: null })
      },

      // 注意：isLoggedIn 不放在 state 里，
      // 因为 Zustand set() 展开时会把 getter 固化成静态值。
      // 各组件改用 selector：useAppStore(s => !!s.user && !!s.token)

      // ---- TTS / 当前输入状态 ----
      currentText: '',
      currentLanguage: 'zh-CN',
      currentVoice: '',
      audioUrl: null,
      fromCache: false,
      isLoading: false,

      setCurrentText: (text) => set({ currentText: text }),
      setCurrentLanguage: (lang) => set({ currentLanguage: lang }),
      setCurrentVoice: (voice) => set({ currentVoice: voice }),
      setAudioUrl: (url, fromCache = false) => {
        const old = get().audioUrl
        if (old && old.startsWith('blob:')) {
          URL.revokeObjectURL(old)
        }
        set({ audioUrl: url, fromCache })
      },
      setIsLoading: (loading) => set({ isLoading: loading }),

      // ---- 语言列表（从后端加载一次，缓存起来）----
      languages: [],
      setLanguages: (langs) => set({ languages: langs }),

      // ---- 收藏总数（导航栏角标用）----
      favoritesCount: 0,
      setFavoritesCount: (n) => set({ favoritesCount: n }),
    }),
    {
      name: 'tcc-app-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        currentLanguage: state.currentLanguage,
      }),
      // persist 恢复完成后把 _hasHydrated 设为 true
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    },
  ),
)

export default useAppStore
