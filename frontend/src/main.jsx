import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'   // 必须在这里引入，Tailwind 样式才会生效

// ReactDOM.createRoot 是 React 18 的新写法
// 旧写法是 ReactDOM.render，React 18 已废弃
// createRoot 支持并发特性（Concurrent Features），性能更好
ReactDOM.createRoot(document.getElementById('root')).render(
  // StrictMode 在开发环境会故意渲染两次，帮你发现副作用问题
  // 生产环境自动关闭，不影响性能
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
