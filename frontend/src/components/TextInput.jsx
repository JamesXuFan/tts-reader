// ============================================================
// TextInput 组件 — 文字输入区域
// ============================================================
// 这是一个"受控组件"（Controlled Component）
// 受控的意思：输入框的值由 React state 控制，不是 DOM 自己管
// 好处：父组件随时可以读取、清空、修改输入内容
// ============================================================

const MAX_CHARS = 1000   // 最大字符限制

function TextInput({ value, onChange, disabled = false }) {
  const charCount = value.length
  const isOverLimit = charCount > MAX_CHARS

  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-gray-700 mb-1.5">
        输入文字
      </label>
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="在这里输入想要朗读的文字..."
          rows={6}
          className={`input-base resize-none text-base leading-relaxed ${
            isOverLimit ? 'border-red-400 focus:ring-red-400' : ''
          } ${disabled ? 'bg-gray-50 cursor-not-allowed' : ''}`}
        />
        {/* 字数统计，右下角显示 */}
        <div
          className={`absolute bottom-2 right-3 text-xs select-none ${
            isOverLimit ? 'text-red-500 font-medium' : 'text-gray-400'
          }`}
        >
          {charCount} / {MAX_CHARS}
        </div>
      </div>

      {/* 超出字数限制时的提示 */}
      {isOverLimit && (
        <p className="mt-1 text-xs text-red-500">
          文字超出 {MAX_CHARS} 字限制，请减少内容
        </p>
      )}

      {/* 快捷操作按钮 */}
      <div className="mt-1.5 flex gap-2">
        <button
          type="button"
          onClick={() => onChange('')}
          disabled={disabled || !value}
          className="text-xs text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          清空
        </button>
        <span className="text-gray-200">|</span>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.readText().then((text) => onChange(text)).catch(() => {})
          }}
          disabled={disabled}
          className="text-xs text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
        >
          粘贴
        </button>
      </div>
    </div>
  )
}

export default TextInput
