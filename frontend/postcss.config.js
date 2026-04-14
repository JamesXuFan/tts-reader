// PostCSS 是 CSS 的预处理器，Tailwind 需要通过它来工作
// autoprefixer 自动添加 -webkit- 等浏览器前缀，保证兼容性
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
