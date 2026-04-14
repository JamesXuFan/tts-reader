import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import useAppStore from '../store/useAppStore'

// ============================================================
// Layout 组件 — 全局导航栏 + 页面内容区域
// ============================================================
// Outlet 是 React Router 的关键概念：
// 它是一个"占位符"，子路由的页面会渲染在这里
// 比如访问 /favorites，Outlet 位置就会显示 FavoritesPage
// ============================================================

function Layout() {
  const user = useAppStore((s) => s.user)
  const isLoggedIn = useAppStore((s) => !!s.user && !!s.token)
  const logout = useAppStore((s) => s.logout)
  const favoritesCount = useAppStore((s) => s.favoritesCount)
  const navigate = useNavigate()
  const location = useLocation()

  // 判断当前路由，高亮对应导航链接
  const isActive = (path) => location.pathname === path

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* ---- 顶部导航栏 ---- */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          {/* Logo + 品牌名 */}
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary-500 hover:text-primary-600">
            <span className="text-2xl">🔊</span>
            <span>TCC 朗读</span>
          </Link>

          {/* 中间导航链接 */}
          <nav className="hidden sm:flex items-center gap-1">
            <NavLink to="/" active={isActive('/')}>
              首页
            </NavLink>
            {isLoggedIn && (
              <NavLink to="/favorites" active={isActive('/favorites')}>
                我的收藏
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
                  退出
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="btn-primary text-sm"
              >
                登录
              </Link>
            )}
          </div>
        </div>

        {/* 手机端底部导航（小屏幕显示） */}
        <div className="sm:hidden border-t border-gray-100 flex">
          <MobileNavLink to="/" active={isActive('/')}>
            首页
          </MobileNavLink>
          {isLoggedIn && (
            <MobileNavLink to="/favorites" active={isActive('/favorites')}>
              收藏
            </MobileNavLink>
          )}
        </div>
      </header>

      {/* ---- 页面内容区域 ---- */}
      {/* Outlet 渲染当前路由对应的子页面 */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* ---- 底部 Footer ---- */}
      <footer className="bg-white border-t border-gray-100 py-4 text-center text-xs text-gray-400">
        TCC 朗读 &copy; {new Date().getFullYear()}
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
