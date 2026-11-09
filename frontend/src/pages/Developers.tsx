import React, { useState, useEffect } from 'react'
import {
  Key,
  Code2,
  BarChart3,
  Plus,
  Copy,
  Check,
  Trash2,
  AlertTriangle,
  ShieldAlert,
  Zap,
  Activity,
  Terminal,
} from 'lucide-react'
import {
  developersApi,
  type ApiKeyItem,
  type ApiKeyCreated,
  type ApiStats,
} from '../api/developers'
import { useToast } from '../hooks/useToast'

type TabType = 'keys' | 'docs' | 'stats'
type LangType = 'curl' | 'python' | 'nodejs'

export default function Developers() {
  const [activeTab, setActiveTab] = useState<TabType>('keys')
  const [keys, setKeys] = useState<ApiKeyItem[]>([])
  const [stats, setStats] = useState<ApiStats | null>(null)
  const [isLoadingKeys, setIsLoadingKeys] = useState(false)
  const [isLoadingStats, setIsLoadingStats] = useState(false)
  const [selectedLang, setSelectedLang] = useState<LangType>('curl')

  // Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreated | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [copiedKey, setCopiedKey] = useState(false)
  const [copiedSnippetId, setCopiedSnippetId] = useState<string | null>(null)

  const toast = useToast()

  // Fetch API keys
  const fetchKeys = async () => {
    setIsLoadingKeys(true)
    try {
      const data = await developersApi.listKeys()
      setKeys(data)
    } catch {
      toast.error('Không thể tải danh sách API Key.')
    } finally {
      setIsLoadingKeys(false)
    }
  }

  // Fetch Usage Stats
  const fetchStats = async () => {
    setIsLoadingStats(true)
    try {
      const data = await developersApi.getStats(7)
      setStats(data)
    } catch {
      toast.error('Không thể tải thống kê sử dụng.')
    } finally {
      setIsLoadingStats(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'keys') {
      fetchKeys()
    } else if (activeTab === 'stats') {
      fetchStats()
    }
  }, [activeTab])

  // Handle create key
  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName.trim()) {
      toast.error('Vui lòng nhập tên cho API Key.')
      return
    }

    setIsCreating(true)
    try {
      const created = await developersApi.createKey(newKeyName.trim())
      setCreatedKeyData(created)
      toast.success('Đã tạo API Key mới thành công!')
      fetchKeys()
    } catch {
      toast.error('Không thể tạo API Key lúc này.')
    } finally {
      setIsCreating(false)
    }
  }

  // Handle revoke key
  const handleRevokeKey = async (id: number, name: string) => {
    if (!window.confirm(`Bạn có chắc chắn muốn thu hồi API Key "${name}"? Thao tác này không thể hoàn tác.`)) {
      return
    }

    try {
      await developersApi.revokeKey(id)
      toast.success(`Đã thu hồi API Key "${name}".`)
      fetchKeys()
    } catch {
      toast.error('Không thể thu hồi API Key.')
    }
  }

  // Copy to clipboard
  const handleCopy = (text: string, snippetId?: string) => {
    navigator.clipboard.writeText(text)
    if (snippetId) {
      setCopiedSnippetId(snippetId)
      setTimeout(() => setCopiedSnippetId(null), 2000)
    } else {
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2000)
    }
    toast.success('Đã sao chép vào bộ nhớ tạm!')
  }

  // Code snippets generator
  const getCodeSnippets = (lang: LangType) => {
    if (lang === 'curl') {
      return {
        voices: `curl -X GET "https://api.voxify.ai/v1/voices" \\
  -H "Authorization: Bearer vx_live_YOUR_API_KEY"`,
        ttsSync: `curl -X POST "https://api.voxify.ai/v1/tts" \\
  -H "Authorization: Bearer vx_live_YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Chào mừng bạn đến với hệ thống giọng nói thông minh Voxify.",
    "voice": "vi-VN-HoaiMyNeural",
    "mode": "sync"
  }'`,
        ttsAsync: `curl -X POST "https://api.voxify.ai/v1/tts" \\
  -H "Authorization: Bearer vx_live_YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Bản tin thời sự tổng hợp buổi tối với thời lượng dài...",
    "voice": "vi-VN-NamMinhNeural",
    "mode": "async",
    "webhook_url": "https://your-domain.com/webhooks/voxify"
  }'`,
        jobStatus: `curl -X GET "https://api.voxify.ai/v1/jobs/123" \\
  -H "Authorization: Bearer vx_live_YOUR_API_KEY"`,
        credits: `curl -X GET "https://api.voxify.ai/v1/credits" \\
  -H "Authorization: Bearer vx_live_YOUR_API_KEY"`,
      }
    }

    if (lang === 'python') {
      return {
        voices: `import requests

url = "https://api.voxify.ai/v1/voices"
headers = {"Authorization": "Bearer vx_live_YOUR_API_KEY"}

response = requests.get(url, headers=headers)
print(response.json())`,
        ttsSync: `import requests

url = "https://api.voxify.ai/v1/tts"
headers = {
    "Authorization": "Bearer vx_live_YOUR_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "text": "Chào mừng bạn đến với hệ thống giọng nói thông minh Voxify.",
    "voice": "vi-VN-HoaiMyNeural",
    "mode": "sync"
}

response = requests.post(url, json=payload, headers=headers)
result = response.json()
print("Audio URL:", result["audio_url"])`,
        ttsAsync: `import requests

url = "https://api.voxify.ai/v1/tts"
headers = {
    "Authorization": "Bearer vx_live_YOUR_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "text": "Bản tin thời sự tổng hợp buổi tối...",
    "voice": "vi-VN-NamMinhNeural",
    "mode": "async",
    "webhook_url": "https://your-domain.com/webhooks/voxify"
}

response = requests.post(url, json=payload, headers=headers)
job_info = response.json()
print("Job ID:", job_info["job_id"])`,
        jobStatus: `import requests

job_id = 123
url = f"https://api.voxify.ai/v1/jobs/{job_id}"
headers = {"Authorization": "Bearer vx_live_YOUR_API_KEY"}

response = requests.get(url, headers=headers)
print(response.json())`,
        credits: `import requests

url = "https://api.voxify.ai/v1/credits"
headers = {"Authorization": "Bearer vx_live_YOUR_API_KEY"}

response = requests.get(url, headers=headers)
print("Số dư credit:", response.json()["credit_balance"])`,
      }
    }

    // Node.js
    return {
      voices: `const axios = require('axios');

async function getVoices() {
  const res = await axios.get('https://api.voxify.ai/v1/voices', {
    headers: { Authorization: 'Bearer vx_live_YOUR_API_KEY' }
  });
  console.log(res.data);
}
getVoices();`,
      ttsSync: `const axios = require('axios');

async function createSyncTTS() {
  const res = await axios.post(
    'https://api.voxify.ai/v1/tts',
    {
      text: 'Chào mừng bạn đến với hệ thống giọng nói thông minh Voxify.',
      voice: 'vi-VN-HoaiMyNeural',
      mode: 'sync'
    },
    {
      headers: { Authorization: 'Bearer vx_live_YOUR_API_KEY' }
    }
  );
  console.log('Audio URL:', res.data.audio_url);
}
createSyncTTS();`,
      ttsAsync: `const axios = require('axios');

async function createAsyncTTS() {
  const res = await axios.post(
    'https://api.voxify.ai/v1/tts',
    {
      text: 'Bản tin thời sự tổng hợp buổi tối...',
      voice: 'vi-VN-NamMinhNeural',
      mode: 'async',
      webhook_url: 'https://your-domain.com/webhooks/voxify'
    },
    {
      headers: { Authorization: 'Bearer vx_live_YOUR_API_KEY' }
    }
  );
  console.log('Job ID:', res.data.job_id);
}
createAsyncTTS();`,
      jobStatus: `const axios = require('axios');

async function checkJob(jobId) {
  const res = await axios.get(\`https://api.voxify.ai/v1/jobs/\${jobId}\`, {
    headers: { Authorization: 'Bearer vx_live_YOUR_API_KEY' }
  });
  console.log('Job status:', res.data.status, 'Progress:', res.data.progress);
}
checkJob(123);`,
      credits: `const axios = require('axios');

async function getCredits() {
  const res = await axios.get('https://api.voxify.ai/v1/credits', {
    headers: { Authorization: 'Bearer vx_live_YOUR_API_KEY' }
  });
  console.log('Balance:', res.data.credit_balance);
}
getCredits();`,
    }
  }

  const snippets = getCodeSnippets(selectedLang)

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Terminal className="w-7 h-7 text-primary" />
            Cổng Thông Tin Lập Trình Viên (Developer Portal)
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Quản lý API Key bảo mật, tra cứu tài liệu tương tác và giám sát lượng sử dụng Public API v1.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 p-1 bg-muted/50 rounded-xl border border-border/50 self-start md:self-auto">
          <button
            onClick={() => setActiveTab('keys')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'keys'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Key className="w-4 h-4 text-primary" />
            Quản Lý API Key
          </button>
          <button
            onClick={() => setActiveTab('docs')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'docs'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Code2 className="w-4 h-4 text-indigo-400" />
            Tài Liệu API v1
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'stats'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            Thống Kê Sử Dụng
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: API KEY MANAGEMENT */}
      {/* =================================================================== */}
      {activeTab === 'keys' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-card border border-border/50 shadow-sm">
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                Khóa Truy Cập Public API (API Keys)
              </h2>
              <p className="text-xs text-muted-foreground">
                API Key được băm mật mã chuẩn SHA-256 trong cơ sở dữ liệu. Không chia sẻ khóa này với bất kỳ ai.
              </p>
            </div>
            <button
              onClick={() => {
                setNewKeyName('')
                setCreatedKeyData(null)
                setIsCreateModalOpen(true)
              }}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Tạo API Key Mới
            </button>
          </div>

          {/* List of Keys */}
          <div className="rounded-2xl border border-border/50 bg-card overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border/40 flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Danh sách khóa ({keys.length})
              </span>
              <button
                onClick={fetchKeys}
                className="text-xs text-primary hover:underline font-medium"
              >
                Làm mới
              </button>
            </div>

            {isLoadingKeys ? (
              <div className="py-16 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Đang tải danh sách khóa...
              </div>
            ) : keys.length === 0 ? (
              <div className="py-16 text-center space-y-3">
                <Key className="w-10 h-10 text-muted-foreground/40 mx-auto" />
                <p className="text-sm text-foreground font-medium">Bạn chưa tạo API Key nào</p>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Hãy nhấn &ldquo;Tạo API Key Mới&rdquo; để bắt đầu tích hợp giọng nói Voxify vào ứng dụng của bạn.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/30 text-muted-foreground border-b border-border/40">
                    <tr>
                      <th className="py-3.5 px-4 font-semibold">Tên gợi nhớ</th>
                      <th className="py-3.5 px-4 font-semibold">Mã nhận diện (Prefix)</th>
                      <th className="py-3.5 px-4 font-semibold">Trạng thái</th>
                      <th className="py-3.5 px-4 font-semibold">Ngày tạo</th>
                      <th className="py-3.5 px-4 font-semibold">Lần dùng cuối</th>
                      <th className="py-3.5 px-4 font-semibold text-right">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {keys.map((k) => (
                      <tr key={k.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3.5 px-4 font-medium text-foreground">
                          {k.name}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-muted-foreground">
                          <span className="px-2.5 py-1 rounded-md bg-muted text-foreground/90 text-[11px] border border-border/40">
                            {k.key_prefix}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          {k.is_active ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                              Hoạt động
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              Đã thu hồi
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">
                          {new Date(k.created_at).toLocaleString('vi-VN')}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">
                          {k.last_used_at ? new Date(k.last_used_at).toLocaleString('vi-VN') : 'Chưa sử dụng'}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {k.is_active && (
                            <button
                              onClick={() => handleRevokeKey(k.id, k.name)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Thu hồi API Key"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Thu hồi
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: INTERACTIVE DOCUMENTATION */}
      {/* =================================================================== */}
      {activeTab === 'docs' && (
        <div className="space-y-8">
          {/* Base URL & Auth Card */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-2">
              <span className="text-xs font-semibold text-primary uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="w-4 h-4" />
                Base URL
              </span>
              <div className="p-3 bg-muted/60 rounded-xl font-mono text-xs text-foreground select-all border border-border/40">
                https://api.voxify.ai/v1
              </div>
              <p className="text-xs text-muted-foreground">
                Tất cả request phải được thực hiện qua giao thức HTTPS bảo mật.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-2">
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <Key className="w-4 h-4" />
                Xác thực (Authentication)
              </span>
              <div className="p-3 bg-muted/60 rounded-xl font-mono text-xs text-foreground select-all border border-border/40">
                Authorization: Bearer vx_live_...
              </div>
              <p className="text-xs text-muted-foreground">
                Gắn API Key vào Header cho mỗi yêu cầu.
              </p>
            </div>
          </div>

          {/* Language Switcher for Code Samples */}
          <div className="flex items-center justify-between border-b border-border/40 pb-3">
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Code2 className="w-5 h-5 text-indigo-400" />
              Mẫu Mã Nguồn (Code Snippets)
            </h3>
            <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-xl border border-border/50">
              {(['curl', 'python', 'nodejs'] as LangType[]).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setSelectedLang(lang)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    selectedLang === lang
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {lang === 'curl' ? 'cURL' : lang === 'python' ? 'Python' : 'Node.js'}
                </button>
              ))}
            </div>
          </div>

          {/* Endpoints List */}
          <div className="space-y-6">
            {/* Endpoint 1: Voices */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    GET
                  </span>
                  <span className="font-mono text-sm font-semibold text-foreground">/v1/voices</span>
                </div>
                <button
                  onClick={() => handleCopy(snippets.voices, 'voices')}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Sao chép mã"
                >
                  {copiedSnippetId === 'voices' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Lấy danh sách các giọng đọc hệ thống tiếng Việt và các giọng clone độc quyền của bạn.
              </p>
              <pre className="p-4 bg-muted/40 rounded-xl overflow-x-auto text-xs font-mono text-muted-foreground border border-border/30">
                {snippets.voices}
              </pre>
            </div>

            {/* Endpoint 2: Sync TTS */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    POST
                  </span>
                  <span className="font-mono text-sm font-semibold text-foreground">/v1/tts (Chế độ Sync)</span>
                </div>
                <button
                  onClick={() => handleCopy(snippets.ttsSync, 'ttsSync')}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Sao chép mã"
                >
                  {copiedSnippetId === 'ttsSync' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Tổng hợp âm thanh trực tiếp và nhận về URL phát/tải audio ngay lập tức.
              </p>
              <pre className="p-4 bg-muted/40 rounded-xl overflow-x-auto text-xs font-mono text-muted-foreground border border-border/30">
                {snippets.ttsSync}
              </pre>
            </div>

            {/* Endpoint 3: Async TTS */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    POST
                  </span>
                  <span className="font-mono text-sm font-semibold text-foreground">/v1/tts (Chế độ Async & Webhook)</span>
                </div>
                <button
                  onClick={() => handleCopy(snippets.ttsAsync, 'ttsAsync')}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Sao chép mã"
                >
                  {copiedSnippetId === 'ttsAsync' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Tạo background job cho các văn bản dài (lên tới 50.000 ký tự). Nhận webhook POST khi hoàn thành.
              </p>
              <pre className="p-4 bg-muted/40 rounded-xl overflow-x-auto text-xs font-mono text-muted-foreground border border-border/30">
                {snippets.ttsAsync}
              </pre>
            </div>

            {/* Endpoint 4: Jobs Status */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    GET
                  </span>
                  <span className="font-mono text-sm font-semibold text-foreground">/v1/jobs/{'{id}'}</span>
                </div>
                <button
                  onClick={() => handleCopy(snippets.jobStatus, 'jobStatus')}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Sao chép mã"
                >
                  {copiedSnippetId === 'jobStatus' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Tra cứu tiến trình hoàn thành (0 - 100%) và lấy link audio của Job bất đồng bộ.
              </p>
              <pre className="p-4 bg-muted/40 rounded-xl overflow-x-auto text-xs font-mono text-muted-foreground border border-border/30">
                {snippets.jobStatus}
              </pre>
            </div>

            {/* Endpoint 5: Credits */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    GET
                  </span>
                  <span className="font-mono text-sm font-semibold text-foreground">/v1/credits</span>
                </div>
                <button
                  onClick={() => handleCopy(snippets.credits, 'credits')}
                  className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Sao chép mã"
                >
                  {copiedSnippetId === 'credits' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Kiểm tra số dư credit hiện tại, cấp độ gói cước và hạn mức gọi API/phút.
              </p>
              <pre className="p-4 bg-muted/40 rounded-xl overflow-x-auto text-xs font-mono text-muted-foreground border border-border/30">
                {snippets.credits}
              </pre>
            </div>
          </div>

          {/* Rate Limits & Status Codes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Rate Limiting */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                Hạn Mức Rate Limit Theo Gói Cước
              </h4>
              <p className="text-xs text-muted-foreground">
                Mỗi phản hồi API đều chứa các Header chuẩn: <code className="text-foreground">X-RateLimit-Limit</code>,{' '}
                <code className="text-foreground">X-RateLimit-Remaining</code>,{' '}
                <code className="text-foreground">X-RateLimit-Reset</code>.
              </p>
              <div className="rounded-xl border border-border/40 overflow-hidden text-xs">
                <table className="w-full text-left">
                  <thead className="bg-muted/40 text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3 font-medium">Gói cước</th>
                      <th className="py-2.5 px-3 font-medium text-right">Giới hạn</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    <tr>
                      <td className="py-2.5 px-3 text-foreground">Free (Miễn phí)</td>
                      <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">20 req/phút</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 text-foreground">Pro</td>
                      <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">60 req/phút</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 text-foreground">VIP / Enterprise</td>
                      <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">120 req/phút</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 text-foreground">Admin</td>
                      <td className="py-2.5 px-3 font-mono text-right text-muted-foreground">300 req/phút</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* HTTP Status Codes */}
            <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-3">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                Bảng Mã Phản Hồi Chuẩn (HTTP Status)
              </h4>
              <div className="rounded-xl border border-border/40 overflow-hidden text-xs">
                <table className="w-full text-left">
                  <thead className="bg-muted/40 text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3 font-medium">Mã</th>
                      <th className="py-2.5 px-3 font-medium">Mô tả chi tiết</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    <tr>
                      <td className="py-2 px-3 font-mono font-bold text-emerald-400">200 / 202</td>
                      <td className="py-2 px-3 text-muted-foreground">Thành công / Job đã đưa vào hàng đợi</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-mono font-bold text-amber-400">401</td>
                      <td className="py-2 px-3 text-muted-foreground">API Key không hợp lệ hoặc đã bị thu hồi</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-mono font-bold text-rose-400">402</td>
                      <td className="py-2 px-3 text-muted-foreground">Số dư credit không đủ (Insufficient Credits)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-mono font-bold text-amber-400">429</td>
                      <td className="py-2 px-3 text-muted-foreground">Vượt quá tần suất rate limit (kèm Retry-After)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-mono font-bold text-rose-500">500</td>
                      <td className="py-2 px-3 text-muted-foreground">Lỗi xử lý từ máy chủ Voxify</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: USAGE STATISTICS */}
      {/* =================================================================== */}
      {activeTab === 'stats' && (
        <div className="space-y-6">
          {isLoadingStats ? (
            <div className="py-20 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              Đang tổng hợp dữ liệu thống kê...
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Tổng số yêu cầu (7 ngày)</span>
                    <Activity className="w-4 h-4 text-primary" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {stats.total_requests.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-muted-foreground">Bao gồm cả Sync và Async</p>
                </div>

                <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Credit đã tiêu thụ</span>
                    <Zap className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {stats.total_credits.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-muted-foreground">Tự động đồng bộ với tài khoản web</p>
                </div>

                <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Tỷ lệ thành công</span>
                    <Check className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">100%</div>
                  <p className="text-[11px] text-emerald-400 font-medium">Hệ thống ổn định</p>
                </div>

                <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-1">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Khóa API đang mở</span>
                    <Key className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {keys.filter((k) => k.is_active).length}
                  </div>
                  <p className="text-[11px] text-muted-foreground">Đang hoạt động</p>
                </div>
              </div>

              {/* Daily Usage Chart / Table */}
              <div className="p-5 rounded-2xl bg-card border border-border/50 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-primary" />
                    Biểu Đồ & Chi Tiết Lượng Gọi Theo Ngày
                  </h3>
                  <span className="text-xs text-muted-foreground">7 ngày qua</span>
                </div>

                <div className="space-y-3 pt-2">
                  {stats.daily_usage.map((day) => {
                    const maxReq = Math.max(...stats.daily_usage.map((d) => d.requests), 1)
                    const percent = Math.round((day.requests / maxReq) * 100)

                    return (
                      <div key={day.date} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono text-foreground font-medium">{day.date}</span>
                          <span className="text-muted-foreground">
                            <strong className="text-foreground">{day.requests}</strong> requests &bull;{' '}
                            <strong className="text-amber-400">{day.credits}</strong> credits
                          </span>
                        </div>
                        <div className="h-2.5 w-full bg-muted/60 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(percent, 2)}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="py-20 text-center text-muted-foreground text-sm">
              Không có dữ liệu thống kê.
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: CREATE API KEY */}
      {/* =================================================================== */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-card border border-border/60 shadow-2xl space-y-5">
            {!createdKeyData ? (
              <form onSubmit={handleCreateKey} className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Key className="w-5 h-5 text-primary" />
                    Tạo API Key Mới
                  </h3>
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Đóng
                  </button>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">
                    Tên gợi nhớ cho khóa <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="ví dụ: Production Server, Next.js App..."
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-muted/50 border border-border/50 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Đặt tên dễ nhớ để phân biệt mục đích sử dụng của từng API Key.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    Hủy bỏ
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-all disabled:opacity-50"
                  >
                    {isCreating ? 'Đang tạo...' : 'Tạo Khóa Ngay'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-emerald-400 flex items-center gap-2">
                    <Check className="w-5 h-5" />
                    Tạo API Key Thành Công!
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Khóa cho: <strong className="text-foreground">{createdKeyData.name}</strong>
                  </p>
                </div>

                {/* Important Warning */}
                <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                  <div>
                    <strong>CẢNH BÁO BẢO MẬT QUAN TRỌNG:</strong> Đây là lần duy nhất bạn có thể xem khóa API đầy đủ này.
                    Sau khi đóng cửa sổ này, chúng tôi sẽ không thể hiển thị lại khóa cho bạn.
                  </div>
                </div>

                {/* Full Key Box */}
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-foreground">API Key Bí Mật</label>
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-muted font-mono text-xs text-foreground border border-border/50">
                    <span className="truncate flex-1 select-all">{createdKeyData.raw_key}</span>
                    <button
                      type="button"
                      onClick={() => handleCopy(createdKeyData.raw_key)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shrink-0"
                    >
                      {copiedKey ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedKey ? 'Đã chép' : 'Sao chép'}
                    </button>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreateModalOpen(false)
                      setCreatedKeyData(null)
                    }}
                    className="px-5 py-2 rounded-xl bg-muted text-foreground text-xs font-semibold hover:bg-muted/80 transition-colors"
                  >
                    Tôi đã lưu khóa an toàn &bull; Đóng
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
