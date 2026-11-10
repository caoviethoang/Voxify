import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import TermsOfService from './TermsOfService'
import PrivacyPolicy from './PrivacyPolicy'
import RefundPolicy from './RefundPolicy'

describe('Legal Pages (Issue #16)', () => {
  it('renders Terms of Service page with key sections and warnings', () => {
    render(
      <MemoryRouter>
        <TermsOfService />
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { level: 1, name: /Điều Khoản Dịch Vụ/i })).toBeInTheDocument()
    expect(screen.getByText(/Quy Định Cấm Tuyệt Đối/i)).toBeInTheDocument()
    expect(screen.getByText(/Chính Sách Cảnh Báo & Khóa Tài Khoản/i)).toBeInTheDocument()
  })

  it('renders Privacy Policy page with encryption and rights sections', () => {
    render(
      <MemoryRouter>
        <PrivacyPolicy />
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { level: 1, name: /Chính Sách Bảo Mật/i })).toBeInTheDocument()
    expect(screen.getByText(/1\. Dữ Liệu Chúng Tôi Thu Thập/i)).toBeInTheDocument()
    expect(screen.getByText(/2\. Tiêu Chuẩn Bảo Mật & Mã Hóa/i)).toBeInTheDocument()
  })

  it('renders Refund Policy page with auto-refund and rules', () => {
    render(
      <MemoryRouter>
        <RefundPolicy />
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { level: 1, name: /Chính Sách Hoàn Tiền/i })).toBeInTheDocument()
    expect(screen.getByText(/1\. Tự Động Hoàn Credit Khi Tác Vụ Lỗi/i)).toBeInTheDocument()
    expect(screen.getByText(/3\. Các Trường Hợp Từ Chối Hoàn Tiền/i)).toBeInTheDocument()
  })
})
