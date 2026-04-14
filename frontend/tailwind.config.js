/** @type {import('tailwindcss').Config} */
export default {
  // content 告诉 Tailwind 扫描哪些文件，只保留用到的 CSS 类
  // 这样最终打包的 CSS 文件体积很小
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      // 自定义主色调，方便全局统一修改
      colors: {
        primary: {
          50:  '#eff6ff',
          100: '#dbeafe',
          500: '#3B82F6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
    },
  },
  plugins: [],
}
