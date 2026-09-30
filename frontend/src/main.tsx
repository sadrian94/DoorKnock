import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { TimeZoneProvider } from './TimeZoneContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TimeZoneProvider><App /></TimeZoneProvider>
  </StrictMode>,
)
