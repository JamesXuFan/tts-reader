import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import FavoritesPage from './pages/FavoritesPage'

// App 是整个应用的根组件，负责路由配置
// BrowserRouter 使用浏览器的 History API 实现路由
// 路由就像一个"地址到页面的映射表"
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Layout 包裹所有页面，提供统一的导航栏 */}
        <Route path="/" element={<Layout />}>
          {/* index 表示访问 "/" 时显示的默认子页面 */}
          <Route index element={<HomePage />} />
          <Route path="favorites" element={<FavoritesPage />} />
        </Route>
        {/* 登录页面不需要导航栏，单独放 */}
        <Route path="/login" element={<LoginPage />} />
        {/* 访问未知路由，重定向回首页 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
