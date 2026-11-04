import { useState, useEffect, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'
import BottomTabBar from '../components/layout/BottomTabBar'
import AnnouncementBar from '../components/ui/AnnouncementBar'
import ToastContainer from '../components/ui/Toast'

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('voxify_sidebar_collapsed') === 'true'
  })
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)

  const handleToggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem('voxify_sidebar_collapsed', String(next))
      return next
    })
  }, [])

  // Phím tắt 'B' để bật/tắt thu gọn sidebar (khi không gõ trong ô văn bản)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (
        target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
      ) {
        return
      }

      if (e.key === 'b' || e.key === 'B') {
        if (!e.metaKey && !e.ctrlKey && !e.altKey) {
          e.preventDefault()
          handleToggleCollapse()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleToggleCollapse])

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B0D12] text-slate-900 dark:text-white flex flex-col font-sans antialiased selection:bg-indigo-500 selection:text-white">
      {/* 1. Thanh thông báo khuyến mãi / sự kiện trên cùng */}
      <AnnouncementBar />

      <div className="flex-1 flex min-h-0">
        {/* 2. Desktop Sidebar */}
        <div className="hidden lg:block flex-shrink-0 sticky top-0 h-screen z-40">
          <Sidebar
            collapsed={collapsed}
            onToggleCollapse={handleToggleCollapse}
          />
        </div>

        {/* 3. Mobile Drawer Backdrop & Sidebar */}
        {mobileDrawerOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
              onClick={() => setMobileDrawerOpen(false)}
            />
            <div className="fixed inset-y-0 left-0 max-w-[260px] w-full z-10 shadow-2xl animate-in slide-in-from-left duration-150">
              <Sidebar
                collapsed={false}
                onToggleCollapse={() => {}}
                isMobile={true}
                onCloseMobile={() => setMobileDrawerOpen(false)}
              />
            </div>
          </div>
        )}

        {/* 4. Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar onOpenMobileMenu={() => setMobileDrawerOpen(true)} />

          {/* Dynamic Page Outlet: pb-16 trên mobile để tránh che bởi BottomTabBar */}
          <main className="flex-1 p-3 sm:p-5 lg:p-6 w-full mx-auto pb-18 md:pb-6 overflow-x-hidden">
            <Outlet />
          </main>
        </div>
      </div>

      {/* 5. Mobile Bottom Tab Bar (dưới 768px) */}
      <BottomTabBar />

      {/* 6. Global Toast Container */}
      <ToastContainer />
    </div>
  )
}
