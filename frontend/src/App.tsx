import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import AppLayout from './layouts/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import TextToSpeech from './pages/TextToSpeech'
import PlaceholderPage from './pages/PlaceholderPage'
import Profile from './pages/Profile'
import NotFound from './pages/NotFound'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import VerifyEmail from './pages/VerifyEmail'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public auth pages */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />

            {/* Protected Dashboard shell */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              {/* Trang chính: Bảng điều khiển */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />

              {/* Trang Text to Speech (giữ nguyên đầy đủ tính năng tạo giọng) */}
              <Route path="/tts" element={<TextToSpeech />} />
              <Route path="/voice/tts" element={<TextToSpeech />} />

              {/* Trang cá nhân */}
              <Route path="/profile" element={<Profile />} />

              {/* Các trang placeholder cho các mục sidebar */}
              <Route
                path="/tools"
                element={
                  <PlaceholderPage
                    title="Công cụ AI"
                    subtitle="Kho công cụ AI đa năng xử lý âm thanh, văn bản và hình ảnh."
                  />
                }
              />
              <Route
                path="/history"
                element={
                  <PlaceholderPage
                    title="Lịch Sử Xử Lý"
                    subtitle="Quản lý và tải lại toàn bộ các đoạn âm thanh và video bạn đã tạo."
                  />
                }
              />
              <Route
                path="/pricing"
                element={
                  <PlaceholderPage
                    title="Nâng Cấp Gói & Nạp Credit"
                    subtitle="Chọn gói linh hoạt phù hợp với nhu cầu sáng tạo không giới hạn của bạn."
                  />
                }
              />
              <Route
                path="/affiliate"
                element={
                  <PlaceholderPage
                    title="Chương Trình Affiliate (25%)"
                    subtitle="Giới thiệu Voxify tới cộng đồng và nhận 25% hoa hồng trọn đời."
                  />
                }
              />
              <Route
                path="/developers"
                element={
                  <PlaceholderPage
                    title="API & Developers"
                    subtitle="Tích hợp API giọng đọc AI tiếng Việt chất lượng cao vào ứng dụng của bạn."
                  />
                }
              />

              {/* 404 bên trong layout */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
