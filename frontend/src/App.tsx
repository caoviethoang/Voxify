import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './context/ToastContext'
import AppLayout from './layouts/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import TextToSpeech from './pages/TextToSpeech'
import VoiceLibrary from './pages/VoiceLibrary'
import CreditHistory from './pages/CreditHistory'
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
            {/* Các trang đăng nhập / đăng ký công khai */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />

            {/* Layout chính được bảo vệ bởi ProtectedRoute */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              {/* Trang chủ: Bảng điều khiển */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />

              {/* Studio Tạo giọng nói (Text to Speech 3 cột) */}
              <Route path="/studio" element={<TextToSpeech />} />
              <Route path="/tts" element={<TextToSpeech />} />
              <Route path="/voice/tts" element={<TextToSpeech />} />

              {/* Thư viện giọng đọc */}
              <Route path="/voices" element={<VoiceLibrary />} />

              {/* Lịch sử giao dịch Credit */}
              <Route path="/credits" element={<CreditHistory />} />
              <Route path="/credits/history" element={<CreditHistory />} />

              {/* Hồ sơ người dùng */}
              <Route path="/profile" element={<Profile />} />

              {/* Các trang công cụ, lịch sử, mở rộng */}
              <Route
                path="/history"
                element={
                  <PlaceholderPage
                    title="Lịch Sử Xử Lý"
                    subtitle="Quản lý và tải lại toàn bộ các đoạn âm thanh và video bạn đã tạo trong các phiên trước."
                  />
                }
              />
              <Route
                path="/pricing"
                element={
                  <PlaceholderPage
                    title="Gói Cước & Nạp Credit"
                    subtitle="Lựa chọn các gói cước linh hoạt phù hợp với nhu cầu sáng tạo không giới hạn của bạn."
                  />
                }
              />
              <Route
                path="/affiliate"
                element={
                  <PlaceholderPage
                    title="Giới Thiệu Bạn Bè (Affiliate 25%)"
                    subtitle="Chia sẻ Voxify tới đồng nghiệp & cộng đồng để nhận ngay 25% hoa hồng trọn đời."
                  />
                }
              />
              <Route
                path="/developers"
                element={
                  <PlaceholderPage
                    title="API & Developers"
                    subtitle="Tích hợp API giọng đọc AI tiếng Việt chất lượng cao vào website và ứng dụng của bạn."
                  />
                }
              />

              {/* Trang 404 */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
