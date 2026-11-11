import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAudioTools, useAudioToolJobs } from '../hooks/useAudioTools'
import { ToolIcon } from '../components/tools/ToolIcon'
import {
  Wrench,
  Search,
  Zap,
  Sparkles,
  Download,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

export default function AudioToolsHub() {
  const navigate = useNavigate()
  const { data: toolsData, isLoading, error } = useAudioTools()
  const { data: recentJobs, isLoading: jobsLoading } = useAudioToolJobs()
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  const categories = useMemo(() => {
    return toolsData?.categories || []
  }, [toolsData])

  const allTools = useMemo(() => {
    return categories.flatMap((c) => c.tools)
  }, [categories])

  const filteredTools = useMemo(() => {
    return allTools.filter((tool) => {
      const matchCat = selectedCategory === 'all' || tool.category === selectedCategory
      const query = search.toLowerCase().trim()
      const matchQuery =
        !query ||
        tool.name_vi.toLowerCase().includes(query) ||
        tool.name_en.toLowerCase().includes(query) ||
        tool.description_vi.toLowerCase().includes(query)
      return matchCat && matchQuery
    })
  }, [allTools, selectedCategory, search])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* 1. Header Banner */}
      <div className="rounded-2xl p-6 sm:p-8 bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/50 border border-indigo-500/20 backdrop-blur-sm relative overflow-hidden">
        <div className="relative z-10 max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Bộ công cụ âm thanh chuyên nghiệp</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Nền tảng Công cụ Âm thanh (Audio Tools Hub)
          </h1>
          <p className="text-sm text-slate-300 dark:text-white/70 leading-relaxed">
            Bộ công cụ xử lý, chỉnh sửa, khử tạp âm và tách âm thanh bằng AI được tối ưu hóa toàn diện.
            Dễ dàng xâu chuỗi nhiều công cụ để tạo nên sản phẩm hoàn hảo.
          </p>
        </div>
      </div>

      {/* 2. Search & Category Filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm công cụ (cắt ghép, lọc tạp âm, đổi đuôi...)"
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] rounded-xl text-xs sm:text-sm text-slate-800 dark:text-white placeholder:text-slate-400 focus:outline-none focus:border-indigo-500 transition-colors shadow-xs"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              selectedCategory === 'all'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white dark:bg-[#12151C] text-slate-600 dark:text-white/70 border border-slate-200 dark:border-white/[0.08] hover:bg-slate-50'
            }`}
          >
            Tất cả ({allTools.length})
          </button>
          {categories.map((c) => (
            <button
              key={c.category}
              type="button"
              onClick={() => setSelectedCategory(c.category)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                selectedCategory === c.category
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white dark:bg-[#12151C] text-slate-600 dark:text-white/70 border border-slate-200 dark:border-white/[0.08] hover:bg-slate-50'
              }`}
            >
              {c.meta?.title_vi || c.category} ({c.tools.length})
            </button>
          ))}
        </div>
      </div>

      {/* 3. Tools Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-44 rounded-2xl bg-slate-100 dark:bg-white/[0.03] animate-pulse border border-slate-200 dark:border-white/[0.05]"
            />
          ))}
        </div>
      ) : error ? (
        <div className="p-8 rounded-2xl bg-red-500/10 border border-red-500/20 text-center text-red-500 text-sm">
          Không thể tải danh sách công cụ âm thanh. Vui lòng thử lại sau.
        </div>
      ) : filteredTools.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-slate-400">
          Không tìm thấy công cụ nào phù hợp với từ khóa &quot;{search}&quot;.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTools.map((tool) => (
            <div
              key={tool.id}
              onClick={() => navigate(`/tools/${tool.id}`)}
              className="group relative p-5 rounded-2xl bg-white dark:bg-[#0E1117] border border-slate-200 dark:border-white/[0.08] hover:border-indigo-500 dark:hover:border-indigo-500/60 shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center group-hover:scale-105 transition-transform">
                    <ToolIcon name={tool.icon} className="w-5 h-5" />
                  </div>

                  <div className="flex items-center gap-1.5">
                    {tool.cost_type === 'free' ? (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        Miễn phí
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {tool.cost_credits} cr/phút
                      </span>
                    )}

                    {tool.heavy && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                        GPU AI
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors flex items-center gap-1.5">
                    <span>{tool.name_vi}</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-white/50 mt-1 line-clamp-2 leading-relaxed">
                    {tool.description_vi}
                  </p>
                </div>
              </div>

              <div className="pt-4 mt-3 border-t border-slate-100 dark:border-white/[0.05] flex items-center justify-between text-xs font-medium text-indigo-600 dark:text-indigo-400">
                <span>Mở công cụ</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 4. Recent Jobs Section */}
      <div className="space-y-4 pt-6 border-t border-slate-200 dark:border-white/[0.08]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
              Lịch sử xử lý công cụ gần đây
            </h2>
          </div>
        </div>

        {jobsLoading ? (
          <div className="p-4 text-center text-xs text-slate-400">Đang tải lịch sử...</div>
        ) : !recentJobs || recentJobs.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-50 dark:bg-[#12151C] border border-slate-200 dark:border-white/[0.08] text-center text-xs text-slate-400">
            Chưa có tác vụ xử lý nào. Hãy chọn một công cụ phía trên để bắt đầu!
          </div>
        ) : (
          <div className="bg-white dark:bg-[#0E1117] rounded-xl border border-slate-200 dark:border-white/[0.08] divide-y divide-slate-100 dark:divide-white/[0.05] overflow-hidden">
            {recentJobs.slice(0, 5).map((job) => (
              <div
                key={job.id}
                className="p-3.5 sm:px-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center flex-shrink-0">
                    <Wrench className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-900 dark:text-white truncate flex items-center gap-2">
                      <span>{job.tool_name_vi || job.tool_id}</span>
                      <span className="text-[10px] text-slate-400 font-normal">
                        ({job.input_filename || 'Tệp đầu vào'})
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2">
                      <span>
                        {new Date(job.created_at).toLocaleString('vi-VN')}
                      </span>
                      {job.credit_used > 0 && (
                        <span>• {job.credit_used} credit</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {job.status === 'done' && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Hoàn tất
                    </span>
                  )}
                  {job.status === 'processing' && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      {job.progress}%
                    </span>
                  )}
                  {job.status === 'failed' && (
                    <span className="inline-flex items-center gap-1 text-[11px] text-red-500 font-medium" title={job.error_message || ''}>
                      <AlertCircle className="w-3.5 h-3.5" />
                      Thất bại
                    </span>
                  )}

                  {job.status === 'done' && (
                    <a
                      href={job.download_url}
                      download
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-white/10 dark:hover:bg-white/15 text-slate-700 dark:text-white transition-colors flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" />
                      <span>Tải về</span>
                    </a>
                  )}

                  <Link
                    to={`/tools/${job.tool_id}`}
                    state={{ source_tool_job_id: job.id }}
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    Mở lại
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
