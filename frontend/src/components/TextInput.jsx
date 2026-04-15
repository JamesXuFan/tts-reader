import { useT } from '../hooks/useT'

const MAX_CHARS = 1000

function TextInput({ value, onChange, disabled = false }) {
  const t = useT()
  const charCount = value.length
  const isOverLimit = charCount > MAX_CHARS

  return (
    <div className="w-full">
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={t('textinput.placeholder')}
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
          {charCount} / {MAX_CHARS} {t('textinput.limit')}
        </div>
      </div>

      {/* 超出字数限制时的提示 */}
      {isOverLimit && (
        <p className="mt-1 text-xs text-red-500">
          {t('home.err.toolong')}
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
          {t('textinput.clear')}
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
          {t('textinput.paste')}
        </button>
      </div>
    </div>
  )
}

export default TextInput
