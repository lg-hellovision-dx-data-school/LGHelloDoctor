import { SERVICE_NAME } from '../brand'
import type { ChatApiResponse, EmergencyInfo, Hospital } from '../types/chat'

/**
 * 채팅 API — 브라우저가 **항상** 이 주소로 직접 POST 합니다. (/api/chat 사용 안 함)
 * ngrok 주소가 바뀌면 아래 CHAT_API_URL 만 수정하면 됩니다.
 */
export const CHAT_API_URL =
  'https://johanne-crystallographic-miguelina.ngrok-free.dev/chat'

export function getChatApiUrl(): string {
  const env = import.meta.env.VITE_CHAT_API_URL?.trim()
  if (env && /^https?:\/\//i.test(env)) {
    return env
  }
  return CHAT_API_URL
}

export type ChatRequestBody = {
  text: string
  session_id: string
  lat: number
  lng: number
}

function messageForHttpStatus(status: number): string {
  switch (status) {
    case 502:
      return `${SERVICE_NAME} 서버에 일시적인 문제가 있습니다(502). 잠시 후 다시 시도해 주세요.`
    case 503:
      return '서비스가 잠시 사용할 수 없습니다(503). 잠시 후 다시 시도해 주세요.'
    case 504:
      return '서버 응답이 너무 늦습니다(504). 잠시 후 다시 시도해 주세요.'
    case 500:
    case 501:
      return '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
    case 429:
      return '요청이 많습니다. 잠시 후 다시 시도해 주세요.'
    case 401:
    case 403:
      return '접근이 허용되지 않습니다. 관리자에게 문의해 주세요.'
    case 404:
      return '요청 주소를 찾을 수 없습니다(404). 서버 주소가 맞는지 확인해 주세요.'
    default:
      return `요청에 실패했습니다(상태 코드 ${status}). 잠시 후 다시 시도해 주세요.`
  }
}

function parseHospitalEntry(raw: unknown): Hospital | null {
  if (typeof raw !== 'object' || raw === null) return null
  const o = raw as Record<string, unknown>
  const name = o.name
  const address = o.address
  const phone = o.phone
  const distance = o.distance
  const navi_url = o.navi_url
  const walk_time = o.walk_time
  if (
    typeof name !== 'string' ||
    typeof address !== 'string' ||
    typeof phone !== 'string' ||
    typeof navi_url !== 'string' ||
    typeof walk_time !== 'number'
  ) {
    return null
  }
  const distNum =
    typeof distance === 'number'
      ? distance
      : typeof distance === 'string'
        ? Number(distance)
        : NaN
  if (!Number.isFinite(distNum)) return null

  let drive_time: number | null = null
  if (o.drive_time === null || o.drive_time === undefined) {
    drive_time = null
  } else if (typeof o.drive_time === 'number' && Number.isFinite(o.drive_time)) {
    drive_time = o.drive_time
  } else if (typeof o.drive_time === 'string') {
    const d = Number(o.drive_time)
    drive_time = Number.isFinite(d) ? d : null
  }

  return {
    name,
    address,
    phone,
    distance: distNum,
    navi_url,
    drive_time,
    walk_time,
  }
}

function parseEmergency(raw: unknown): EmergencyInfo | null {
  if (typeof raw !== 'object' || raw === null) return null
  const o = raw as { is_emergency?: unknown; severity?: unknown }
  if (typeof o.is_emergency !== 'boolean') return null
  const severity = typeof o.severity === 'string' ? o.severity : 'LOW'
  return { is_emergency: o.is_emergency, severity }
}

function parseChatResponse(data: unknown): ChatApiResponse {
  if (typeof data !== 'object' || data === null) {
    throw new Error('응답 형식이 올바르지 않습니다. 관리자에게 문의해 주세요.')
  }
  const answer = (data as { answer?: unknown }).answer
  if (typeof answer !== 'string' || !answer.trim()) {
    throw new Error('응답에 답변 내용이 없습니다. 잠시 후 다시 시도해 주세요.')
  }

  let hospitals: Hospital[] = []
  const rawH = (data as { hospitals?: unknown }).hospitals
  if (Array.isArray(rawH)) {
    hospitals = rawH
      .map(parseHospitalEntry)
      .filter((h): h is Hospital => h !== null)
  }

  const emergencyRaw = (data as { emergency?: unknown }).emergency
  const emergency =
    emergencyRaw === undefined || emergencyRaw === null
      ? null
      : parseEmergency(emergencyRaw)

  const intentRaw = (data as { intent?: unknown }).intent
  const intent = typeof intentRaw === 'string' ? intentRaw : undefined

  return {
    answer: answer.trim(),
    intent,
    hospitals,
    emergency: emergency ?? undefined,
  }
}

export async function postChat(body: ChatRequestBody): Promise<ChatApiResponse> {
  const url = getChatApiUrl()
  let res: Response
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': '69420',
      },
      body: JSON.stringify(body),
    })
  } catch (e) {
    if (e instanceof TypeError) {
      throw new Error(
        '네트워크에 연결할 수 없습니다. 인터넷 연결을 확인하거나 서버 상태를 확인해 주세요.',
      )
    }
    throw e
  }

  const raw = await res.text()
  let json: unknown

  try {
    json = raw ? JSON.parse(raw) : null
  } catch {
    if (!res.ok) {
      throw new Error(messageForHttpStatus(res.status))
    }
    throw new Error('서버 응답을 이해할 수 없습니다. 잠시 후 다시 시도해 주세요.')
  }

  if (!res.ok) {
    const detail =
      typeof json === 'object' &&
      json !== null &&
      'detail' in json &&
      typeof (json as { detail?: unknown }).detail === 'string'
        ? (json as { detail: string }).detail.trim()
        : ''

    if (detail) {
      throw new Error(detail)
    }

    throw new Error(messageForHttpStatus(res.status))
  }

  return parseChatResponse(json)
}
