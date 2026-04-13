import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }

type State = { hasError: boolean }

/**
 * TV 화면 내부(예: QR 생성 실패) 렌더 오류 시 앱 전체가 빈 회색 화면이 되지 않도록 막습니다.
 */
export class TvErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[HelloBee TV]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      const base = import.meta.env.BASE_URL.replace(/\/$/, '') || ''
      return (
        <div
          style={{
            minHeight: '100svh',
            background: '#1a202c',
            color: '#fef08a',
            padding: '2rem',
            fontFamily: "'Noto Sans KR', system-ui, sans-serif",
            fontSize: '1.2rem',
            lineHeight: 1.5,
          }}
        >
          <p style={{ fontWeight: 700 }}>TV 화면을 표시하는 중 문제가 발생했습니다.</p>
          <p style={{ color: '#e2e8f0', marginTop: '0.75rem', fontSize: '1rem' }}>
            병원 정보·QR 데이터가 비정상일 때 발생할 수 있어요. 아래에서 다시 시도하거나 일반 채팅으로
            이동해 주세요.
          </p>
          <p style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <a href={`${base}/?tv=1`} style={{ color: '#fff', fontWeight: 600 }}>
              TV 화면 다시 열기
            </a>
            <a href={import.meta.env.BASE_URL} style={{ color: '#fff', fontWeight: 600 }}>
              일반 채팅
            </a>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
