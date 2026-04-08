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
}

export type ChatApiResponse = {
  answer: string
  intent?: string
  hospitals: Hospital[]
  emergency?: EmergencyInfo | null
}

export type InputMode = 'voice' | 'text'
