import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, register } from '../api/client'
import useAppStore from '../store/useAppStore'
import { useT } from '../hooks/useT'

function LoginPage() {
  const navigate = useNavigate()
  const { setUser } = useAppStore()
  const t = useT()

  const [mode, setMode] = useState('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

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
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await login(email, password)
      const userObj = { id: data.user_id, username: data.username, email: data.email }
      setUser(userObj, data.access_token)
      navigate('/')
    } catch (err) {
      const msg = err.response?.data?.detail
      if (typeof msg === 'string') {
        setError(msg)
      } else {
        setError(t('login.err.failed'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError(t('register.err.mismatch'))
      return
    }
    if (password.length < 6) {
      setError(t('register.err.short'))
      return
    }

    setLoading(true)
    try {
      await register(username, email, password)
      setSuccessMsg(t('register.success'))
      switchMode('login')
      setEmail(email)
    } catch (err) {
      const msg = err.response?.data?.detail
      if (typeof msg === 'string') {
        setError(msg)
      } else if (Array.isArray(msg)) {
        setError(msg[0]?.msg || t('register.err.failed'))
      } else {
        setError(t('register.err.failed'))
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
            <span className="text-3xl">✏️</span>
            {t('app.name')}
          </Link>
          <p className="text-gray-500 text-sm mt-1">{t('login.subtitle')}</p>
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
                {m === 'login' ? t('login.tab') : t('login.registerTab')}
              </button>
            ))}
          </div>

          <div className="p-6">
            {successMsg && (
              <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
                {successMsg}
              </div>
            )}

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
                    {t('login.email')}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('login.emailPlaceholder')}
                    required
                    autoFocus
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t('login.password')}
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('login.passwordPlaceholder')}
                    required
                    className="input-base"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-2.5 mt-2"
                >
                  {loading ? t('login.submitting') : t('login.submit')}
                </button>
              </form>
            )}

            {/* 注册表单 */}
            {mode === 'register' && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t('register.username')}
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={t('register.usernamePlaceholder')}
                    required
                    minLength={2}
                    maxLength={20}
                    autoFocus
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t('login.email')}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('login.emailPlaceholder')}
                    required
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t('login.password')}
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('register.passwordPlaceholder')}
                    required
                    minLength={6}
                    className="input-base"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    {t('register.confirm')}
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder={t('register.confirmPlaceholder')}
                    required
                    className="input-base"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-2.5 mt-2"
                >
                  {loading ? t('register.submitting') : t('register.submit')}
                </button>
              </form>
            )}

            <div className="mt-4 text-center">
              <Link to="/" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
                {t('login.guestLink')}
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
