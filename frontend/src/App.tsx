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
import History from './pages/History'
import Pricing from './pages/Pricing'
import PlaceholderPage from './pages/PlaceholderPage'
import Developers from './pages/Developers'
import Profile from './pages/Profile'
import NotFound from './pages/NotFound'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import VerifyEmail from './pages/VerifyEmail'
import TermsOfService from './pages/TermsOfService'
import PrivacyPolicy from './pages/PrivacyPolicy'
import RefundPolicy from './pages/RefundPolicy'

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

            {/* Các trang pháp lý công khai (Issue #16) */}
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/refund" element={<RefundPolicy />} />
            <Route path="/refund-policy" element={<RefundPolicy />} />

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
              <Route path="/history" element={<History />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route
                path="/affiliate"
                element={
                  <PlaceholderPage
                    title="Giới Thiệu Bạn Bè (Affiliate 25%)"
                    subtitle="Chia sẻ Voxify tới đồng nghiệp & cộng đồng để nhận ngay 25% hoa hồng trọn đời."
                  />
                }
              />
              <Route path="/developers" element={<Developers />} />

              {/* Trang 404 */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
