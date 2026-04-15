import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import useAppStore from '../store/useAppStore'
import { useT } from '../hooks/useT'

// ============================================================
// Layout 组件 — 全局导航栏 + 页面内容区域
// ============================================================

function Layout() {
  const user = useAppStore((s) => s.user)
  const isLoggedIn = useAppStore((s) => !!s.user && !!s.token)
  const logout = useAppStore((s) => s.logout)
  const favoritesCount = useAppStore((s) => s.favoritesCount)
  const uiLang = useAppStore((s) => s.uiLang)
  const setUiLang = useAppStore((s) => s.setUiLang)
  const navigate = useNavigate()
  const location = useLocation()
  const t = useT()

  const isActive = (path) => location.pathname === path

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const toggleLang = () => setUiLang(uiLang === 'zh' ? 'en' : 'zh')

  return (
    <div className="min-h-screen flex flex-col">
      {/* ---- 顶部导航栏 ---- */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          {/* Logo + 品牌名 */}
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary-500 hover:text-primary-600">
            <span className="text-2xl">✏️</span>
            <span>{t('app.name')}</span>
          </Link>

          {/* 中间导航链接 */}
          <nav className="hidden sm:flex items-center gap-1">
            <NavLink to="/" active={isActive('/')}>
              {t('nav.home')}
            </NavLink>
            {isLoggedIn && (
              <NavLink to="/favorites" active={isActive('/favorites')}>
                {t('nav.favorites')}
                {favoritesCount > 0 && (
                  <span className="ml-1.5 text-xs bg-primary-100 text-primary-600 px-1.5 py-0.5 rounded-full">
                    {favoritesCount}
                  </span>
                )}
              </NavLink>
            )}
          </nav>

          {/* 右侧用户区 */}
          <div className="flex items-center gap-3">
            {/* 语言切换按钮 */}
            <button
              onClick={toggleLang}
              className="text-xs font-medium px-2 py-1 rounded border border-gray-200 text-gray-500 hover:border-primary-400 hover:text-primary-500 transition-colors select-none"
              title={uiLang === 'zh' ? 'Switch to English' : '切换到中文'}
            >
              {uiLang === 'zh' ? 'EN' : '中'}
            </button>

            {isLoggedIn ? (
              <>
                {/* 字母头像 + 用户名 */}
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-primary-500 text-white flex items-center justify-center text-sm font-bold select-none">
                    {user?.username?.[0]?.toUpperCase() ?? '?'}
                  </div>
                  <span className="text-sm font-medium text-gray-800 hidden sm:block">
                    {user?.username}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-sm text-gray-500 hover:text-red-500 transition-colors"
                >
                  {t('nav.logout')}
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="btn-primary text-sm"
              >
                {t('nav.login')}
              </Link>
            )}
          </div>
        </div>

        {/* 手机端底部导航（小屏幕显示） */}
        <div className="sm:hidden border-t border-gray-100 flex">
          <MobileNavLink to="/" active={isActive('/')}>
            {t('nav.home')}
          </MobileNavLink>
          {isLoggedIn && (
            <MobileNavLink to="/favorites" active={isActive('/favorites')}>
              {t('nav.favorites')}
            </MobileNavLink>
          )}
        </div>
      </header>

      {/* ---- 页面内容区域 ---- */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* ---- 底部 Footer ---- */}
      <footer className="bg-white border-t border-gray-100 py-4 text-center text-xs text-gray-400">
        {t('app.name')} &copy; {new Date().getFullYear()}
      </footer>
    </div>
  )
}

// 桌面端导航链接组件
function NavLink({ to, active, children }) {
  return (
    <Link
      to={to}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        active
          ? 'bg-primary-50 text-primary-600'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
      }`}
    >
      {children}
    </Link>
  )
}

// 手机端导航链接组件
function MobileNavLink({ to, active, children }) {
  return (
    <Link
      to={to}
      className={`flex-1 py-2 text-center text-sm font-medium transition-colors ${
        active ? 'text-primary-500 border-b-2 border-primary-500' : 'text-gray-500'
      }`}
    >
      {children}
    </Link>
  )
}

export default Layout
