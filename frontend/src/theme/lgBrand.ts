/**
 * LG HelloDoctor 디자인 토큰 (Apple HIG + Senior-friendly).
 * App 루트 인라인 style 과 public/lg-hello-theme.css 와 동일 값을 유지한다.
 */
export const LG_BRAND_CSS_VARS: Record<string, string> = {
  // 브랜드 액센트 (LG Red)
  '--chat-primary': '#a50034',
  '--chat-primary-rgb': '165, 0, 52',
  '--chat-primary-15': 'rgba(165, 0, 52, 0.15)',
  '--chat-primary-20': 'rgba(165, 0, 52, 0.2)',
  '--chat-primary-35': 'rgba(165, 0, 52, 0.35)',
  '--chat-accent-bg': '#fdf2f5',

  // Apple-style 페이지·카드
  '--chat-page-bg': '#f5f5f7',
  '--chat-card': '#ffffff',
  '--chat-card-soft': '#fbfbfd',

  // 텍스트
  '--chat-text': '#1d1d1f',
  '--chat-text-secondary': '#424245',
  '--chat-muted': '#6e6e73',
  '--chat-muted-soft': '#86868b',

  // 컨트롤·구분선
  '--chat-toggle-inactive': '#e8e8ed',
  '--chat-toggle-text': '#1d1d1f',
  '--chat-border': '#d2d2d7',
  '--chat-border-soft': '#e8e8ed',

  // 형태
  '--chat-radius-sm': '0.875rem',
  '--chat-radius-md': '1.25rem',
  '--chat-radius-lg': '1.75rem',
  '--chat-radius-pill': '9999px',

  // 그림자
  '--chat-shadow-xs': '0 1px 2px rgba(0, 0, 0, 0.04)',
  '--chat-shadow-sm': '0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.04)',
  '--chat-shadow-md': '0 8px 24px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.03)',
  '--chat-shadow-lg': '0 20px 48px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.04)',

  // 시니어 친화 최소 타겟·폰트
  '--chat-tap-min': '3.5rem',
  '--chat-tap-lg': '4rem',
  '--chat-font-body': '1.125rem',
  '--chat-font-body-lg': '1.25rem',

  // 모션
  '--chat-ease': 'cubic-bezier(0.4, 0, 0.2, 1)',
  '--chat-ease-out': 'cubic-bezier(0.16, 1, 0.3, 1)',
}
