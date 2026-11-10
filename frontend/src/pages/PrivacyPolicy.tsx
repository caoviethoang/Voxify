import { Link } from 'react-router-dom'
import { ShieldCheck, Lock, Eye, Database, ArrowLeft, Key } from 'lucide-react'

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B0D12] text-slate-800 dark:text-slate-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Navigation back */}
        <div className="mb-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            <ArrowLeft className="w-4 h-4" /> Quay lại trang chủ
          </Link>
        </div>

        {/* Header */}
        <div className="bg-white dark:bg-[#141721] rounded-2xl border border-slate-200 dark:border-white/10 p-8 shadow-sm mb-8">
          <div className="flex items-center gap-3 text-indigo-600 dark:text-indigo-400 mb-2">
            <Lock className="w-6 h-6" />
            <span className="text-xs font-semibold tracking-wider uppercase">Quyền Riêng Tư & An Toàn</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            Chính Sách Bảo Mật (Privacy Policy)
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Cập nhật lần cuối: 10/11/2026 • Tuân thủ chuẩn bảo vệ dữ liệu OWASP & GDPR
          </p>
          <div className="mt-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-900/50 text-xs text-emerald-900 dark:text-emerald-200 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 flex-shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
            <span>
              Tại <strong>Voxify</strong>, quyền riêng tư của bạn là ưu tiên số một. Chúng tôi cam kết <strong>không bao giờ bán dữ liệu</strong> cá nhân, văn bản hay mẫu ghi âm giọng nói của bạn cho bất kỳ bên thứ ba nào.
            </span>
          </div>
        </div>

        {/* Content sections */}
        <div className="bg-white dark:bg-[#141721] rounded-2xl border border-slate-200 dark:border-white/10 p-8 shadow-sm space-y-8 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {/* Mục 1 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Database className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              1. Dữ Liệu Chúng Tôi Thu Thập
            </h2>
            <p className="mb-2">Chúng tôi chỉ thu thập các dữ liệu tối thiểu cần thiết để vận hành dịch vụ:</p>
            <ul className="space-y-1.5 list-disc pl-5">
              <li><strong>Thông tin tài khoản:</strong> Địa chỉ email, họ tên, mật khẩu (được mã hóa một chiều qua thuật toán bcrypt an toàn).</li>
              <li><strong>Dữ liệu văn bản (Text):</strong> Các đoạn văn bản bạn gửi lên để chuyển đổi thành giọng nói.</li>
              <li><strong>Mẫu âm thanh giọng clone:</strong> Các file âm thanh bạn tải lên nhằm phục vụ mục đích huấn luyện hồ sơ giọng AI.</li>
              <li><strong>Thông tin kỹ thuật:</strong> Địa chỉ IP, User-Agent, nhật ký hệ thống nhằm phòng chống tấn công brute-force và lạm dụng tài nguyên.</li>
            </ul>
          </section>

          {/* Mục 2 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Key className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              2. Tiêu Chuẩn Bảo Mật & Mã Hóa
            </h2>
            <div className="grid sm:grid-cols-2 gap-4 mt-3">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                <span className="font-semibold text-slate-900 dark:text-white block mb-1">Mã Hóa Đường Truyền (TLS 1.3)</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Mọi yêu cầu gửi đến API đều được bảo vệ bằng HTTPS với giao thức TLS 1.3 và cơ chế HSTS cưỡng bức kết nối an toàn.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                <span className="font-semibold text-slate-900 dark:text-white block mb-1">Lưu Trữ Mã Hóa (AES-256)</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Các file âm thanh và cơ sở dữ liệu được mã hóa lưu trữ ở trạng thái nghỉ, phân quyền chặt chẽ theo từng người dùng.
                </p>
              </div>
            </div>
          </section>

          {/* Mục 3 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Eye className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              3. Quyền Kiểm Soát Dữ Liệu Của Bạn
            </h2>
            <p className="mb-2">Bạn có toàn quyền đối với dữ liệu của mình bất cứ lúc nào:</p>
            <ul className="space-y-1.5 list-disc pl-5">
              <li><strong>Xem và tải xuống:</strong> Bạn có thể nghe lại và tải về toàn bộ file âm thanh đã tạo trong phần Lịch sử.</li>
              <li><strong>Xóa vĩnh viễn:</strong> Bạn có quyền xóa từng file hoặc xóa hàng loạt. Dữ liệu khi xóa sẽ được tiêu hủy hoàn toàn khỏi máy chủ.</li>
              <li><strong>Xóa tài khoản:</strong> Bạn có quyền yêu cầu xóa toàn bộ tài khoản và mọi dữ liệu liên quan qua trang Hồ sơ hoặc liên hệ hỗ trợ.</li>
            </ul>
          </section>

          {/* Mục 4 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <ShieldCheck className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              4. Cookie & Bảo Mật Phiên Đăng Nhập
            </h2>
            <p>
              Chúng tôi sử dụng <strong>HttpOnly, SameSite=Lax Cookies</strong> để lưu trữ Refresh Token bảo vệ người dùng khỏi tấn công đánh cắp phiên qua XSS. Chúng tôi không sử dụng cookie theo dõi của bên thứ ba nhằm mục đích quảng cáo xâm lấn.
            </p>
          </section>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-white/10 pt-4">
          <span>© 2026 Voxify AI Studio. An toàn & Bảo mật là cam kết hàng đầu.</span>
          <div className="flex gap-4">
            <Link to="/terms" className="hover:text-indigo-600 dark:hover:text-indigo-400">Điều Khoản Dịch Vụ</Link>
            <Link to="/refund" className="hover:text-indigo-600 dark:hover:text-indigo-400">Chính Sách Hoàn Tiền</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
