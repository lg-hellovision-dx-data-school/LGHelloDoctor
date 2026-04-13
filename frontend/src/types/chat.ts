export type ChatRole = 'user' | 'assistant'

/** `/chat` 응답의 병원 카드용 항목 (백엔드 `search_hospital` 근접 스키마) */
export type Hospital = {
  name: string
  address: string
  phone: string
  distance: number
  navi_url: string
  drive_time: number | null
  walk_time: number
}

export type EmergencyInfo = {
  is_emergency: boolean
  severity: string
}

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: number
  hospitals?: Hospital[]
  emergency?: EmergencyInfo | null
  intent?: string
  /** 백엔드 TTS 오디오 URL이 있으면 브라우저에서 재생 후 연속 대화 녹음을 이어갑니다. */
  ttsUrl?: string
  /**
   * false: 추가 질문 필요 → AI 답변 후 호출어 없이 마이크 재개.
   * true: 정보 제공 완료 → 연속 대화 종료 후 호출어 대기.
   */
  ready_for_c?: boolean
}

export type ChatApiResponse = {
  answer: string
  intent?: string
  hospitals: Hospital[]
  emergency?: EmergencyInfo | null
  ttsUrl?: string
  ready_for_c?: boolean
}

export type InputMode = 'voice' | 'text'
