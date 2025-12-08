import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { FDC3Provider } from './context/FDC3Context'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './components/ui/toast'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <FDC3Provider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </FDC3Provider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)
