import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'
import ToastContainer from '../components/ui/Toast'

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('voxify_sidebar_collapsed') === 'true'
  })
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)

  const handleToggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem('voxify_sidebar_collapsed', String(next))
      return next
    })
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0d0d17] text-slate-900 dark:text-white flex font-sans antialiased selection:bg-brand-500 selection:text-white">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block flex-shrink-0 sticky top-0 h-screen z-40">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={handleToggleCollapse}
        />
      </div>

      {/* Mobile Drawer Backdrop & Sidebar */}
      {mobileDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileDrawerOpen(false)}
          />
          {/* Drawer content */}
          <div className="fixed inset-y-0 left-0 max-w-xs w-full z-10 shadow-2xl animate-in slide-in-from-left duration-200">
            <Sidebar
              collapsed={false}
              onToggleCollapse={() => {}}
              isMobile={true}
              onCloseMobile={() => setMobileDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <Topbar onOpenMobileMenu={() => setMobileDrawerOpen(true)} />

        {/* Dynamic Page Outlet */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Global Toast Container */}
      <ToastContainer />
    </div>
  )
}
