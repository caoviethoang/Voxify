import { Link } from 'react-router-dom'
import { Shield, FileText, AlertTriangle, ArrowLeft } from 'lucide-react'

export default function TermsOfService() {
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
            <FileText className="w-6 h-6" />
            <span className="text-xs font-semibold tracking-wider uppercase">Văn bản Pháp lý</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            Điều Khoản Dịch Vụ (Terms of Service)
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Có hiệu lực từ ngày 10/11/2026 • Phiên bản 2.0.0
          </p>
          <div className="mt-4 p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/50 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-3">
            <Shield className="w-5 h-5 flex-shrink-0 text-indigo-600 dark:text-indigo-400 mt-0.5" />
            <span>
              Chào mừng bạn đến với <strong>Voxify AI Studio</strong>. Bằng việc truy cập, đăng ký tài khoản hoặc sử dụng bất kỳ dịch vụ chuyển đổi văn bản và clone giọng nói nào của chúng tôi, bạn đồng ý tuân thủ toàn bộ các điều khoản được quy định dưới đây.
            </span>
          </div>
        </div>

        {/* Content sections */}
        <div className="bg-white dark:bg-[#141721] rounded-2xl border border-slate-200 dark:border-white/10 p-8 shadow-sm space-y-8 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {/* Mục 1 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">1</span>
              Chấp Thuận Điều Khoản & Đăng Ký Tài Khoản
            </h2>
            <p>
              Để sử dụng các tính năng nâng cao, bạn cần đăng ký tài khoản và cung cấp thông tin chính xác, cập nhật. Bạn chịu hoàn toàn trách nhiệm bảo mật thông tin đăng nhập, mật khẩu và mọi hoạt động phát sinh từ tài khoản của mình. Nếu phát hiện hành vi xâm phạm trái phép, bạn cần thông báo ngay lập tức cho đội ngũ Voxify.
            </p>
          </section>

          {/* Mục 2 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">2</span>
              Quyền Sở Hữu Trí Tuệ & Bản Quyền Âm Thanh
            </h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>
                <strong>Nội dung do người dùng tạo (UGC):</strong> Bạn giữ quyền sở hữu đối với nội dung văn bản gốc và các file âm thanh được kết xuất từ dịch vụ, với điều kiện nội dung đó tuân thủ quy chuẩn pháp luật.
              </li>
              <li>
                <strong>Công nghệ và Nền tảng:</strong> Toàn bộ mã nguồn, mô hình AI, thuật toán xử lý âm thanh, giao diện người dùng và thương hiệu Voxify thuộc quyền sở hữu độc quyền của Voxify Studio.
              </li>
              <li>
                <strong>Giọng Clone (Voice Cloning):</strong> Khi tải lên mẫu âm thanh để huấn luyện giọng AI, bạn cam kết bằng văn bản rằng đó là giọng của chính bạn hoặc bạn đã nhận được văn bản ủy quyền hợp pháp từ chủ sở hữu giọng nói.
              </li>
            </ul>
          </section>

          {/* Mục 3 */}
          <section className="p-5 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30">
            <h2 className="text-lg font-bold text-red-700 dark:text-red-400 flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span className="w-6 h-6 rounded-lg bg-red-100 dark:bg-red-900/50 text-red-600 flex items-center justify-center text-xs font-bold">3</span>
              Quy Định Cấm Tuyệt Đối (Content Moderation)
            </h2>
            <p className="mb-3 text-red-900/90 dark:text-red-200/90">
              Hệ thống kiểm duyệt tự động của Voxify sẽ ngay lập tức chặn và lưu vết vi phạm đối với các hành vi sau:
            </p>
            <ul className="space-y-1.5 list-disc pl-5 text-red-800 dark:text-red-300">
              <li>Tạo nội dung kích động bạo lực, khủng bố, vũ khí sát thương, hướng dẫn tự tử.</li>
              <li>Lừa đảo tài chính, chiếm đoạt tài sản, mạo danh cơ quan công an, tòa án, viện kiểm sát hoặc giả mạo yêu cầu chuyển mã OTP ngân hàng.</li>
              <li>Mạo danh nguyên thủ quốc gia, lãnh đạo cấp cao hoặc người nổi tiếng (chống Deepfake voice).</li>
              <li>Nội dung xâm hại tình dục, đồi trụy hoặc quấy rối danh dự nhân phẩm cá nhân.</li>
            </ul>
          </section>

          {/* Mục 4 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">4</span>
              Chính Sách Cảnh Báo & Khóa Tài Khoản (3 Strikes Rule)
            </h2>
            <p className="mb-2">
              Nhằm đảm bảo an toàn tối đa cho cộng đồng, hệ thống Voxify áp dụng cơ chế xử lý vi phạm 3 mức:
            </p>
            <div className="grid sm:grid-cols-3 gap-3 my-4">
              <div className="p-3 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                <span className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase">Lần 1</span>
                <p className="text-xs mt-1 text-slate-500 dark:text-slate-400">Chặn nội dung và gửi cảnh báo vi phạm trong tài khoản.</p>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                <span className="text-xs font-bold text-orange-600 dark:text-orange-400 uppercase">Lần 2</span>
                <p className="text-xs mt-1 text-slate-500 dark:text-slate-400">Cảnh báo nghiêm khắc và giới hạn tạm thời tính năng tạo tác vụ.</p>
              </div>
              <div className="p-3 rounded-lg border border-red-200 dark:border-red-900/40 bg-red-50 dark:bg-red-950/20">
                <span className="text-xs font-bold text-red-600 dark:text-red-400 uppercase">Lần 3</span>
                <p className="text-xs mt-1 text-red-600 dark:text-red-300 font-medium">Khóa tài khoản vĩnh viễn, tịch thu toàn bộ credit hiện có.</p>
              </div>
            </div>
          </section>

          {/* Mục 5 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">5</span>
              Gói Cước, Thanh Toán & Credit
            </h2>
            <p>
              Credit được sử dụng để thanh toán tác vụ chuyển văn bản thành giọng nói và clone giọng. Credit đã mua có thời hạn sử dụng theo từng gói cước được mô tả rõ ràng tại trang Bảng Giá. Chi tiết về điều kiện hoàn credit được quy định tại <Link to="/refund" className="text-indigo-600 dark:text-indigo-400 underline">Chính Sách Hoàn Tiền</Link>.
            </p>
          </section>

          {/* Mục 6 */}
          <section>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-3">
              <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold">6</span>
              Liên Hệ Pháp Lý
            </h2>
            <p>
              Mọi thắc mắc hoặc yêu cầu liên quan đến Điều khoản dịch vụ, vui lòng liên hệ:
            </p>
            <p className="mt-2 font-mono text-xs bg-slate-100 dark:bg-slate-800 p-3 rounded-lg text-slate-700 dark:text-slate-200">
              Email: legal@voxify.app • Hotline: 1900 8888 • Văn phòng: Tòa nhà Công nghệ Voxify, Hà Nội, Việt Nam.
            </p>
          </section>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-white/10 pt-4">
          <span>© 2026 Voxify AI Studio. Mọi quyền được bảo lưu.</span>
          <div className="flex gap-4">
            <Link to="/privacy" className="hover:text-indigo-600 dark:hover:text-indigo-400">Chính Sách Bảo Mật</Link>
            <Link to="/refund" className="hover:text-indigo-600 dark:hover:text-indigo-400">Chính Sách Hoàn Tiền</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
