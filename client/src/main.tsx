import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { FDC3Provider } from './context/FDC3Context'
import { AuthProvider } from './context/AuthContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <FDC3Provider>
        <App />
      </FDC3Provider>
    </AuthProvider>
  </StrictMode>,
)
