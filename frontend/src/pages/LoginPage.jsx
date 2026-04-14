import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, register } from '../api/client'
import useAppStore from '../store/useAppStore'

// ============================================================
// LoginPage — 登录/注册页面
// ============================================================
// 用 Tab 切换登录和注册两种模式
// 登录成功后跳转回首页，并更新全局用户状态
// ============================================================

function LoginPage() {
  const navigate = useNavigate()
  const { setUser } = useAppStore()

  // 控制当前是登录还是注册 tab
  const [mode, setMode] = useState('login')   // 'login' | 'register'

  // 表单字段
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // UI 状态
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // 切换模式时清空表单和提示
  const switchMode = (newMode) => {
    setMode(newMode)
    setError('')
    setSuccessMsg('')
    setEmail('')
    setPassword('')
    setUsername('')
    setConfirmPassword('')
  }

  const handleLogin = async (e) => {
    e.preventDefault()   // 阻止表单默认提交（会刷新页面）
    setError('')
    setLoading(true)

    try {
      const data = await login(email, password)
      // 后端返回平铺字段，手动组装 user 对象
      const userObj = { id: data.user_id, username: data.username, email: data.email }
      setUser(userObj, data.access_token)
      navigate('/')   // 跳转回首页
    } catch (err) {
      const msg = err.response?.data?.detail
      if (typeof msg === 'string') {
        setError(msg)
      } else {
        setError('登录失败，请检查邮箱和密码')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')

    // 前端基础验证
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }
    if (password.length < 6) {
      setError('密码至少需要 6 位')
      return
    }

    setLoading(true)
    try {
      await register(username, email, password)
      setSuccessMsg('注册成功！请登录')
      switchMode('login')
      setEmail(email)   // 自动填入刚注册的邮箱
    } catch (err) {
      const msg = err.response?.data?.detail
      if (typeof msg === 'string') {
        setError(msg)
      } else if (Array.isArray(msg)) {
        // FastAPI 验证错误返回数组格式
        setError(msg[0]?.msg || '注册失败')
      } else {
        setError('注册失败，请重试')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 text-2xl font-bold text-primary-500">
            <span className="text-3xl">🔊</span>
            TCC 朗读
          </Link>
          <p className="text-gray-500 text-sm mt-1">登录后可以收藏和管理朗读内容</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          {/* Tab 切换 */}
          <div className="flex border-b border-gray-100">
            {['login', 'register'].map((m) => (
              <button
                key={m}
                onClick={() => switchMode(m)}
                className={`flex-1 py-3.5 text-sm font-medium transition-colors ${
                  mode === m
                    ? 'text-primary-600 border-b-2 border-primary-500 bg-primary-50'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {m === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* 注册成功提示 */}
            {successMsg && (
              <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
                {successMsg}
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* 登录表单 */}
            {mode === 'login' && (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    邮箱
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    required
                    autoFocus
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    密码
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="输入密码"
                    required
                    className="input-base"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-2.5 mt-2"
                >
                  {loading ? '登录中...' : '登录'}
                </button>
              </form>
            )}

            {/* 注册表单 */}
            {mode === 'register' && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    用户名
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="你的用户名"
                    required
                    minLength={2}
                    maxLength={20}
                    autoFocus
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    邮箱
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    required
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    密码
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="至少 6 位"
                    required
                    minLength={6}
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    确认密码
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="再输入一遍密码"
                    required
                    className="input-base"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-2.5 mt-2"
                >
                  {loading ? '注册中...' : '创建账号'}
                </button>
              </form>
            )}

            {/* 返回首页 */}
            <div className="mt-4 text-center">
              <Link to="/" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
                暂不登录，继续使用
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
