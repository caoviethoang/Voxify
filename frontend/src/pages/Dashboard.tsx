import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import {
  Mic,
  FileText,
  Video,
  Languages,
  Music,
  Disc,
  Play,
  ArrowRight,
  Share2,
  Sparkles,
} from 'lucide-react'

export default function Dashboard() {
  const { t } = useTranslation()
  const { user } = useAuth()

  // Lời chào theo thời gian trong ngày
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return t('greetings.morning') || 'Chào buổi sáng'
    if (hour < 18) return t('greetings.afternoon') || 'Chào buổi chiều'
    return t('greetings.evening') || 'Chào buổi tối'
  }

  const userName = user?.full_name || user?.email.split('@')[0] || 'bạn'

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <span>
              {getGreeting()}, {userName}
            </span>
            <span className="inline-block animate-bounce">👋</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-white/50 mt-1">
            Chào mừng bạn trở lại với không gian sáng tạo giọng nói và nội dung AI của Voxify.
          </p>
        </div>

        <Link
          to="/studio"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
        >
          <Mic className="w-4 h-4" />
          <span>Tạo giọng nói ngay</span>
        </Link>
      </div>

      {/* Row 1: Tiếp tục công việc + Gợi ý + Tạo nhanh */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Tiếp tục công việc */}
        <div className="lg:col-span-5 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
                {t('dashboard.continueWork') || 'Tiếp tục công việc'}
              </span>
              <span className="text-[10px] text-indigo-700 dark:text-indigo-400 font-semibold bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200/60 dark:border-indigo-500/20 px-2 py-0.5 rounded-full">
                Text to Speech
              </span>
            </div>

            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-control bg-indigo-50 dark:bg-white/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white/90 line-clamp-2 leading-snug">
                  Nếu các nghiên cứu chỉ ra rằng tập tạ nhẹ hai mươi cái vẫn giữ cơ tốt ngang tạ nặng...
                </h3>
                <span className="text-[11px] text-slate-500 dark:text-white/40 mt-1 block">
                  Giọng Hoài My (Nữ) &middot; 2 giờ trước
                </span>
              </div>
            </div>

            {/* Dummy audio player */}
            <div className="bg-slate-100/70 dark:bg-black/30 rounded-control p-3 border border-slate-200/60 dark:border-white/5 flex items-center gap-3">
              <button
                className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 transition-colors shadow-xs"
                title="Phát thử"
              >
                <Play className="w-4 h-4 fill-white ml-0.5" />
              </button>
              <div className="flex-1">
                <div className="h-1.5 w-full bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-600 w-1/3 rounded-full" />
                </div>
              </div>
              <span className="text-[11px] font-mono text-slate-500 dark:text-white/40">00:48</span>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-5 pt-4 border-t border-slate-100 dark:border-white/5">
            <Link
              to="/studio"
              className="px-4 py-2 rounded-control bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-xs transition-all"
            >
              {t('common.open') || 'Mở lại'} &rarr;
            </Link>
            <Link
              to="/history"
              className="px-4 py-2 rounded-control bg-white dark:bg-transparent border border-slate-200 dark:border-white/10 text-slate-700 dark:text-white/70 hover:bg-slate-50 dark:hover:bg-white/5 text-xs font-medium transition-colors"
            >
              {t('common.history') || 'Xem lịch sử'}
            </Link>
          </div>
        </div>

        {/* Gợi ý cho bạn */}
        <div className="lg:col-span-4 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs space-y-4">
          <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
            {t('dashboard.suggestedForYou') || 'Gợi ý cho bạn'}
          </span>

          <div className="space-y-3">
            <div className="p-3 rounded-control border border-slate-200/80 dark:border-white/5 bg-slate-50/50 hover:bg-slate-100/60 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] hover:border-indigo-500/30 transition-all flex items-start gap-3 cursor-pointer group">
              <div className="p-2 rounded-control bg-blue-500/10 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {t('dashboard.articleToVideo') || 'Article to Video'}
                  </h4>
                  <span className="text-[9px] font-extrabold px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-0.5 leading-tight">
                  {t('dashboard.articleToVideoDesc') || 'Dán một link bài viết, nhận video ngắn có lồng tiếng sau vài phút.'}
                </p>
              </div>
            </div>

            <div className="p-3 rounded-control border border-slate-200/80 dark:border-white/5 bg-slate-50/50 hover:bg-slate-100/60 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] hover:border-indigo-500/30 transition-all flex items-start gap-3 cursor-pointer group">
              <div className="p-2 rounded-control bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {t('dashboard.autoVideoSeries') || 'Auto Video Series'}
                  </h4>
                  <span className="text-[9px] font-extrabold px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-0.5 leading-tight">
                  {t('dashboard.autoVideoSeriesDesc') || 'Mỗi ngày tự có video mới từ tin tức, GitHub hay RSS, tự động lên kênh.'}
                </p>
              </div>
            </div>

            <div className="p-3 rounded-control border border-slate-200/80 dark:border-white/5 bg-slate-50/50 hover:bg-slate-100/60 dark:bg-[#181C25]/50 dark:hover:bg-[#181C25] hover:border-indigo-500/30 transition-all flex items-start gap-3 cursor-pointer group">
              <div className="p-2 rounded-control bg-rose-500/10 text-rose-600 dark:text-rose-400 mt-0.5 flex-shrink-0">
                <Video className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {t('dashboard.dubbing') || 'Dịch & Lồng tiếng video'}
                  </h4>
                  <span className="text-[9px] font-extrabold px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                    HOT
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-0.5 leading-tight">
                  {t('dashboard.dubbingDesc') || 'Phụ đề, lồng tiếng 100+ ngôn ngữ, giữ nhạc nền gốc.'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tạo nhanh */}
        <div className="lg:col-span-3 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs space-y-3">
          <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
            {t('common.quickCreate') || 'Tạo nhanh'}
          </span>

          <div className="space-y-1">
            <Link
              to="/studio"
              className="flex items-center justify-between p-2.5 rounded-control hover:bg-slate-100 dark:hover:bg-white/5 text-xs text-slate-700 hover:text-slate-900 dark:text-white/80 dark:hover:text-white group transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <Mic className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span>{t('dashboard.createAudioFromText') || 'Tạo audio từ văn bản'}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
            </Link>

            <div className="flex items-center justify-between p-2.5 rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none">
              <div className="flex items-center gap-2.5">
                <FileText className="w-4 h-4" />
                <span>{t('dashboard.createVideoFromArticle') || 'Tạo video từ bài viết'}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none">
              <div className="flex items-center gap-2.5">
                <Video className="w-4 h-4" />
                <span>{t('dashboard.dubVideo') || 'Dịch & Lồng tiếng Video'}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none">
              <div className="flex items-center gap-2.5">
                <Disc className="w-4 h-4" />
                <span>{t('dashboard.cloneVoiceAction') || 'Clone giọng nói (5s)'}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-control text-xs text-slate-400 dark:text-white/30 cursor-not-allowed select-none">
              <div className="flex items-center gap-2.5">
                <Share2 className="w-4 h-4" />
                <span>{t('dashboard.connectSocialChannels') || 'Kết nối kênh mạng xã hội'}</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Khám phá tính năng & Hoạt động gần đây */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Khám phá tính năng */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              {t('common.exploreFeatures') || 'Khám phá tính năng'}
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {/* Card 1: Text to Speech (active) */}
            <Link
              to="/studio"
              className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500/40 shadow-xs hover:shadow-md transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="w-9 h-9 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
                  <Mic className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  Text to Speech
                </h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Chuyển văn bản thành giọng nói AI cảm xúc tự nhiên.
                </p>
              </div>
              <div className="mt-4 pt-2 flex items-center text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
                <span>Tạo ngay</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>

            {/* Card 2: Article to Video */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Article to Video</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-extrabold">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Biến link bài viết thành video ngắn có lồng tiếng.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 3: Dubbing Video */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-3">
                  <Video className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">
                  Dịch & Lồng tiếng Video
                </h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Dịch và lồng tiếng video chuyên nghiệp đa ngôn ngữ.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 4: Music Video */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-3">
                  <Music className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Music Video</h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Video lời bài hát chạy chữ theo nhạc nền.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 5: Speech to Text */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3">
                  <Languages className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Speech to Text</h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Chuyển giọng nói thành văn bản chính xác cao.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 6: Subtitles */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Lồng tiếng phụ đề</h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Chuyển file phụ đề srt thành âm thanh mượt mà.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 7: Audio Translation */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3">
                  <Languages className="w-5 h-5" />
                </div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-white">Dịch Audio</h3>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Dịch và lồng tiếng file audio đa ngôn ngữ.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>

            {/* Card 8: Auto Video Series */}
            <div className="p-4 rounded-card bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between select-none">
              <div>
                <div className="w-9 h-9 rounded-control bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center mb-3">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white">Auto Video Series</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20 font-extrabold">
                    NEW
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-white/50 mt-1 line-clamp-2">
                  Tự động sản xuất video theo lịch trình mỗi ngày.
                </p>
              </div>
              <span className="mt-4 inline-flex items-center self-start text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 dark:bg-white/[0.06] dark:text-white/40 dark:border-white/[0.08]">
                Sắp ra mắt
              </span>
            </div>
          </div>
        </div>

        {/* Hoạt động gần đây */}
        <div className="lg:col-span-4 bg-white dark:bg-[#12151C] rounded-card p-5 border border-slate-200 dark:border-white/[0.08] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-bold tracking-wider text-slate-500 dark:text-white/40 uppercase">
                {t('common.recentActivity') || 'Hoạt động gần đây'}
              </span>
              <span className="text-[11px] text-slate-500 dark:text-white/40">5 ngày qua</span>
            </div>

            <div className="space-y-3">
              <div className="p-2.5 rounded-control hover:bg-slate-50 dark:hover:bg-white/5 transition-colors flex items-center gap-3 cursor-pointer">
                <div className="w-8 h-8 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
                  <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                    Nếu các nghiên cứu chỉ ra rằng...
                  </p>
                  <p className="text-[10px] text-slate-500 dark:text-white/40">
                    Text to Speech &middot; 00:49 &middot; 2 giờ trước
                  </p>
                </div>
              </div>

              <div className="p-2.5 rounded-control hover:bg-slate-50 dark:hover:bg-white/5 transition-colors flex items-center gap-3 cursor-pointer">
                <div className="w-8 h-8 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
                  <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                    Sáu rưỡi chiều sau giờ tan làm, bạn đứng...
                  </p>
                  <p className="text-[10px] text-slate-500 dark:text-white/40">
                    Text to Speech &middot; 02:21 &middot; 2 ngày trước
                  </p>
                </div>
              </div>

              <div className="p-2.5 rounded-control hover:bg-slate-50 dark:hover:bg-white/5 transition-colors flex items-center gap-3 cursor-pointer">
                <div className="w-8 h-8 rounded-control bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
                  <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                    Vì tâm lý thích cảm giác ít êm đềm...
                  </p>
                  <p className="text-[10px] text-slate-500 dark:text-white/40">
                    Text to Speech &middot; 00:33 &middot; 14 giờ trước
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Link
            to="/history"
            className="w-full mt-4 py-2.5 rounded-control border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-center text-xs font-semibold text-slate-700 dark:text-white/70 block transition-colors"
          >
            {t('common.viewAll') || 'Xem tất cả'} &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
