import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { queryClient } from '@/lib/query'
import { AppRouter } from './routes'
import './index.css'

// ===== 全局错误捕获 =====
const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

function reportError(payload: any) {
  try {
    fetch(`${baseUrl}/v1/client-errors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...payload,
        timestamp: new Date().toISOString(),
      }),
    });
  } catch (_) { /* ignore */ }
}

window.onerror = (msg, url, line, col, err) => {
  reportError({
    type: "js_error",
    message: String(msg),
    stack: err?.stack,
    url: url || window.location.href,
  });
  return false;
};

window.addEventListener("unhandledrejection", (e) => {
  reportError({
    type: "promise_rejection",
    message: String(e.reason),
    stack: e.reason?.stack,
    url: window.location.href,
  });
});

// =======================

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppRouter />
      <Toaster />
    </QueryClientProvider>
  </StrictMode>,
)
