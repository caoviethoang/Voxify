/**
 * Design Tokens for Voxify App Shell & Components
 * Theo ngôn ngữ thiết kế riêng:
 * - Nền: #0B0D12, Bề mặt: #12151C / #181C25, Viền: rgba(255, 255, 255, 0.08)
 * - Accent: Gradient Chàm (#6366F1) -> Tím (#8B5CF6)
 * - Màu phụ: Hổ phách (Amber #F59E0B) CHỈ dùng cho Credit và Cảnh báo
 * - Thành công: Xanh lục (#10B981)
 * - Font: "Be Vietnam Pro" (UI) & "JetBrains Mono" (Số liệu/Code)
 * - Bo góc: 14px (Card) & 10px (Button/Input)
 */

export const tokens = {
  colors: {
    bg: {
      dark: '#0B0D12',
      light: '#F8FAFC',
    },
    surface: {
      dark: '#12151C',
      darkElevated: '#181C25',
      light: '#FFFFFF',
      lightElevated: '#F1F5F9',
    },
    border: {
      dark: 'rgba(255, 255, 255, 0.08)',
      darkStrong: 'rgba(255, 255, 255, 0.14)',
      light: 'rgba(0, 0, 0, 0.08)',
    },
    accent: {
      indigo: '#6366F1',
      purple: '#8B5CF6',
      gradient: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
    },
    amber: {
      credit: '#F59E0B',
      warning: '#F59E0B',
    },
    green: {
      success: '#10B981',
    },
  },
  radius: {
    card: '14px',
    control: '10px',
  },
  typography: {
    fontUi: '"Be Vietnam Pro", system-ui, sans-serif',
    fontMono: '"JetBrains Mono", monospace',
  },
  transitions: {
    duration: '150ms',
    timing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const
