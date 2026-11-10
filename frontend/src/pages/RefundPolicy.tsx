import { Link } from 'react-router-dom'
import { RefreshCcw, CheckCircle2, Clock, AlertCircle, ArrowLeft, HelpCircle } from 'lucide-react'

export default function RefundPolicy() {
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
            <RefreshCcw className="w-6 h-6" />
            <span className="text-xs font-semibold tracking-wider uppercase">Chính Sách Khách Hàng</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            Chính Sách Hoàn Tiền (Refund Policy)
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Áp dụng từ ngày 10/11/2026 • Bảo vệ quyền lợi người tiêu dùng
          </p>
          <div className="mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-100 dark:border-blue-900/50 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" />
            <span>
              Voxify cam kết mang lại trải nghiệm tạo giọng nói AI chất lượng cao nhất. Nếu có bất kỳ sự cố kỹ thuật nào khiến bạn không thể sử dụng dịch vụ như cam kết, chúng tôi luôn có cơ chế hoàn trả công bằng và minh bạch.
            </span>
          </div>
        </div>

        {/* Content sections */}
        <div className="bg-white dark:bg-[#141721] rounded-2xl border border-slate-200 dark:border-white/10 p-8 shadow-sm space-y-8 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {/* Mục 1 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              1. Tự Động Hoàn Credit Khi Tác Vụ Lỗi (Auto-Refund)
            </h2>
            <p>
              Đối với dịch vụ chuyển văn bản thành giọng nói (TTS) và Clone giọng:
            </p>
            <ul className="space-y-1.5 list-disc pl-5 mt-2">
              <li>
                Nếu một tác vụ gặp lỗi từ phía máy chủ, nhà cung cấp AI hoặc không thể kết xuất file âm thanh hoàn chỉnh, <strong>hệ thống sẽ tự động hoàn lại 100% số credit đã trừ</strong> ngay lập tức vào số dư của bạn.
              </li>
              <li>
                Giao dịch hoàn trả credit được ghi nhận rõ ràng trong mục <Link to="/credits" className="text-indigo-600 dark:text-indigo-400 underline">Lịch Sử Biến Động Credit</Link>.
              </li>
            </ul>
          </section>

          {/* Mục 2 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <Clock className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              2. Hoàn Tiền Gói Đăng Ký Định Kỳ (Gói Pro & VIP)
            </h2>
            <p className="mb-2">
              Chúng tôi hỗ trợ yêu cầu hoàn tiền cho các đơn hàng mua gói trả phí trong các điều kiện sau:
            </p>
            <div className="grid sm:grid-cols-2 gap-4 mt-3">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                <span className="font-semibold text-slate-900 dark:text-white block mb-1">Thời Hạn Yêu Cầu (7 Ngày)</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Gửi yêu cầu hoàn tiền trong vòng 07 ngày kể từ ngày thanh toán thành công đơn hàng.
                </p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                <span className="font-semibold text-slate-900 dark:text-white block mb-1">Mức Độ Sử Dụng (Dưới 10%)</span>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Tổng số credit hoặc thời lượng giọng đọc đã sử dụng không vượt quá 10% hạn mức ban đầu của gói.
                </p>
              </div>
            </div>
          </section>

          {/* Mục 3 */}
          <section className="p-5 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30">
            <h2 className="text-lg font-bold text-amber-800 dark:text-amber-400 flex items-center gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              3. Các Trường Hợp Từ Chối Hoàn Tiền
            </h2>
            <ul className="space-y-1.5 list-disc pl-5 text-amber-900/90 dark:text-amber-200/90">
              <li>Tài khoản bị khóa do vi phạm chính sách kiểm duyệt nội dung (lừa đảo, mạo danh, bạo lực).</li>
              <li>Yêu cầu hoàn tiền sau khi đã hết thời hạn 07 ngày kể từ khi thanh toán.</li>
              <li>Các gói quà tặng, mã giảm giá khuyến mãi hoặc credit được thưởng miễn phí khi đăng ký.</li>
              <li>Khách hàng thay đổi ý định sau khi đã sử dụng phần lớn dung lượng credit trong gói.</li>
            </ul>
          </section>

          {/* Mục 4 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <HelpCircle className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              4. Quy Trình & Thời Gian Xử Lý
            </h2>
            <ol className="space-y-2 list-decimal pl-5">
              <li>
                <strong>Gửi yêu cầu:</strong> Liên hệ email <code>billing@voxify.app</code> kèm theo Mã đơn hàng (Order Code) và lý do hoàn tiền.
              </li>
              <li>
                <strong>Xem xét & Xác nhận:</strong> Đội ngũ chăm sóc khách hàng sẽ đối soát và phản hồi trong vòng 24 giờ làm việc.
              </li>
              <li>
                <strong>Nhận tiền hoàn:</strong> Tiền hoàn sẽ được chuyển về tài khoản ngân hàng hoặc thẻ thanh toán ban đầu của quý khách trong vòng <strong>3 - 5 ngày làm việc</strong>.
              </li>
            </ol>
          </section>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-white/10 pt-4">
          <span>© 2026 Voxify AI Studio. Mọi thắc mắc vui lòng liên hệ bộ phận thanh toán.</span>
          <div className="flex gap-4">
            <Link to="/terms" className="hover:text-indigo-600 dark:hover:text-indigo-400">Điều Khoản Dịch Vụ</Link>
            <Link to="/privacy" className="hover:text-indigo-600 dark:hover:text-indigo-400">Chính Sách Bảo Mật</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
