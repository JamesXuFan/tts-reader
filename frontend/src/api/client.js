import axios from 'axios'

// ============================================================
// API 客户端 — 封装所有后端接口调用
// ============================================================
// 为什么要封装？
// 1. 统一处理 token 认证（一处修改，全局生效）
// 2. 统一处理错误，不用每次都 try/catch
// 3. 后端地址变了只改这里，不用找遍全部组件
// ============================================================

// 创建 axios 实例，设置基础配置
const api = axios.create({
  baseURL: '/api/v1',           // 配合 vite.config.js 的代理，/api → http://localhost:8000/api
  timeout: 30000,               // 30 秒超时（TTS 合成可能较慢）
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---- 请求拦截器 ----
// 每次发请求前自动附上 JWT token
// 就像每次出门自动带上门卡
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ---- 响应拦截器 ----
// 统一处理 401（token 过期/无效）
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // responseType: 'blob' 时，错误响应体也是 Blob，需要先转成 JSON 才能读 detail
    if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text()
        error.response.data = JSON.parse(text)
      } catch {
        // 解析失败就保持原样
      }
    }

    if (error.response?.status === 401) {
      // token 失效，清除本地存储，跳转登录页
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_info')
      // 避免在登录页再次触发跳转
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

// ============================================================
// TTS 语音合成相关
// ============================================================

/**
 * 合成语音，返回可播放的 audio URL
 * @param {string} text - 要朗读的文字
 * @param {string} language - 语言代码，如 "zh-CN"
 * @param {string} [voiceName] - 可选的声音名称
 * @returns {Promise<string>} 音频的 Blob URL（临时地址，刷新后失效）
 */
export async function speakText(text, language, voiceName = null) {
  const payload = { text, language }
  if (voiceName) payload.voice_name = voiceName

  const response = await api.post('/tts/speak', payload, {
    responseType: 'blob',
  })

  const audioUrl = URL.createObjectURL(response.data)
  // X-From-Cache 响应头由后端设置，true 表示命中缓存，false 表示新生成
  const fromCache = response.headers['x-from-cache'] === 'true'
  return { audioUrl, fromCache }
}

/**
 * 获取支持的语言列表
 * @returns {Promise<Array>} 语言列表
 */
export async function getLanguages() {
  const response = await api.get('/tts/languages')
  return response.data
}

// ============================================================
// 用户认证相关
// ============================================================

/**
 * 登录
 * @returns {Promise<{access_token: string, user: object}>}
 */
export async function login(email, password) {
  // FastAPI OAuth2 登录需要 form 格式（application/x-www-form-urlencoded）
  // 不能用 JSON，这是 OAuth2 标准的要求
  const formData = new URLSearchParams()
  formData.append('username', email)   // FastAPI OAuth2 的字段名是 username
  formData.append('password', password)

  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return response.data
}

/**
 * 注册新用户
 * @returns {Promise<object>} 新建的用户信息
 */
export async function register(username, email, password) {
  const response = await api.post('/auth/register', { username, email, password })
  return response.data
}

/**
 * 获取当前登录用户信息
 * @returns {Promise<object>}
 */
export async function getMe() {
  const response = await api.get('/auth/me')
  return response.data
}

// ============================================================
// 分组相关
// ============================================================

/**
 * 获取所有分组（含每组收藏数）
 */
export async function getGroups() {
  const response = await api.get('/groups/')
  return response.data
}

/**
 * 创建新分组
 * @param {string} name - 分组名称
 * @param {string} [color] - 颜色，如 "#FF5733"
 */
export async function createGroup(name, color = '#3B82F6') {
  const response = await api.post('/groups/', { name, color })
  return response.data
}

/**
 * 更新分组
 */
export async function updateGroup(id, data) {
  const response = await api.put(`/groups/${id}`, data)
  return response.data
}

/**
 * 删除分组（分组内收藏变为"未分组"）
 */
export async function deleteGroup(id) {
  const response = await api.delete(`/groups/${id}`)
  return response.data
}

// ============================================================
// 收藏相关
// ============================================================

/**
 * 获取收藏列表（支持分组过滤和关键词搜索）
 * @param {object} params
 * @param {number} [params.groupId] - 按分组过滤，不传则获取全部
 * @param {string} [params.search] - 搜索关键词
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.pageSize=20] - 每页条数
 */
export async function getFavorites({ groupId, search, page = 1, pageSize = 20 } = {}) {
  const params = { page, page_size: pageSize }
  if (groupId) params.group_id = groupId
  if (search) params.search = search

  const response = await api.get('/favorites/', { params })
  return response.data
}

/**
 * 创建收藏
 * @param {string} title - 标题
 * @param {string} textContent - 文字内容
 * @param {string} language - 语言代码
 * @param {number|null} [groupId] - 所属分组，null 表示未分组
 */
export async function createFavorite(title, textContent, language, groupId = null) {
  const payload = {
    title,
    text_content: textContent,
    language,
  }
  if (groupId) payload.group_id = groupId

  const response = await api.post('/favorites/', payload)
  return response.data
}

/**
 * 更新收藏（修改标题、移动分组等）
 * @param {number} id
 * @param {object} data - 只传要修改的字段，如 { group_id: 3 } 或 { group_id: 0 }（0=移出分组）
 */
export async function updateFavorite(id, data) {
  const response = await api.put(`/favorites/${id}`, data)
  return response.data
}

/**
 * 删除收藏
 */
export async function deleteFavorite(id) {
  const response = await api.delete(`/favorites/${id}`)
  return response.data
}

/**
 * 从收藏中直接播放（后端合成并返回音频）
 */
export async function speakFavorite(id) {
  const response = await api.post(`/favorites/${id}/speak`, {}, {
    responseType: 'blob',
  })
  return URL.createObjectURL(response.data)
}

// 导出 axios 实例，方便特殊情况直接使用
export default api
