import { useState, useCallback, useRef } from 'react'

// ============================================================
// Toast — 轻量通知系统
// ============================================================
// 用法：
//   const { toasts, showToast } = useToast()
//   showToast('操作成功', 'success')
//   <ToastContainer toasts={toasts} />
// ============================================================

export function useToast() {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const showToast = useCallback((message, type = 'success', duration = 3000) => {
    const id = ++idRef.current
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, duration)
  }, [])

  return { toasts, showToast }
}

const STYLES = {
  success: 'bg-green-50 border-green-300 text-green-800',
  error:   'bg-red-50   border-red-300   text-red-800',
  info:    'bg-blue-50  border-blue-300  text-blue-800',
}

const ICONS = {
  success: (
    <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  error: (
    <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  info: (
    <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
}

export function ToastContainer({ toasts }) {
  if (toasts.length === 0) return null
  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl border shadow-lg text-sm font-medium
            animate-fade-in pointer-events-auto max-w-sm ${STYLES[t.type] ?? STYLES.info}`}
        >
          {ICONS[t.type]}
          {t.message}
        </div>
      ))}
    </div>
  )
}
