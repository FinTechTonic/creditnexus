
import { createRoot } from 'react-dom/client'
import './index.css'
import { router } from './router/Routes'
import { RouterProvider } from 'react-router-dom'
import { FDC3Provider } from './context/FDC3Context'
import { AuthProvider } from './context/AuthContext'
import { WalletProvider } from './context/WalletContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './components/ui/toast'
import { ErrorBoundary } from './components/ErrorBoundary'

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found');
}

try {
  createRoot(rootElement).render(
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <WalletProvider>
            <FDC3Provider>
              <ToastProvider>
                <RouterProvider router={router} />
              </ToastProvider>
            </FDC3Provider>
          </WalletProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>,
  )
} catch (renderError) {
  // Show error on screen
  rootElement.innerHTML = `
    <div style="padding: 40px; font-family: monospace; background: #1e1e1e; color: #ff4444; min-height: 100vh;">
      <h1 style="color: #ff6666;">CRITICAL ERROR: React Failed to Render</h1>
      <pre style="background: #000; padding: 20px; border-radius: 4px; overflow: auto; max-width: 800px;">
${renderError instanceof Error ? renderError.message : String(renderError)}
${renderError instanceof Error ? renderError.stack : ''}
      </pre>
      <p style="color: #aaa; margin-top: 20px;">Check the browser console (F12) for more details.</p>
    </div>
  `;
}
