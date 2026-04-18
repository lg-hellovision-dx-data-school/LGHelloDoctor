import { SERVICE_NAME } from '../brand'
import type { ChatApiResponse, EmergencyInfo, Hospital } from '../types/chat'

/**
 * 기본 채팅 API URL.
 * 가급적 .env 의 VITE_CHAT_API_URL 사용을 권장합니다.
 */
export const CHAT_API_URL = 'http://localhost:8000/chat'

export function getChatApiUrl(): string {
  const env = import.meta.env.VITE_CHAT_API_URL?.trim()
  const source = env && /^https?:\/\//i.test(env) ? env : CHAT_API_URL
  // 사용자가 ngrok base URL만 넣어도 동작하도록 /chat을 보정합니다.
  if (/\/chat\/?$/i.test(source)) {
    return source
  }
  return `${source.replace(/\/+$/, '')}/chat`
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

  const name =
    typeof o.name === 'string'
      ? o.name
      : typeof o.hospital_name === 'string'
        ? o.hospital_name
        : typeof o.place_name === 'string'
          ? o.place_name
          : ''
  if (!name.trim()) return null

  const address =
    typeof o.address === 'string'
      ? o.address
      : typeof o.road_address === 'string'
        ? o.road_address
        : typeof o.address_name === 'string'
          ? o.address_name
          : '주소 정보 없음'

  const phone =
    typeof o.phone === 'string'
      ? o.phone
      : typeof o.tel === 'string'
        ? o.tel
        : typeof o.telephone === 'string'
          ? o.telephone
          : '전화번호 정보 없음'

  const distanceRaw = o.distance
  let distNum =
    typeof distanceRaw === 'number'
      ? distanceRaw
      : typeof distanceRaw === 'string'
        ? Number(distanceRaw.replace(/[^\d.]/g, ''))
        : NaN
  if (!Number.isFinite(distNum)) distNum = 0

  const walkRaw = o.walk_time
  let walk_time =
    typeof walkRaw === 'number'
      ? walkRaw
      : typeof walkRaw === 'string'
        ? Number(walkRaw.replace(/[^\d.]/g, ''))
        : NaN
  if (!Number.isFinite(walk_time)) {
    walk_time = Math.max(1, Math.round(distNum / 70))
  }

  let drive_time: number | null = null
  if (o.drive_time === null || o.drive_time === undefined) {
    drive_time = null
  } else if (typeof o.drive_time === 'number' && Number.isFinite(o.drive_time)) {
    drive_time = o.drive_time
  } else if (typeof o.drive_time === 'string') {
    const d = Number(o.drive_time)
    drive_time = Number.isFinite(d) ? d : null
  }

  const navi_url =
    typeof o.navi_url === 'string' && o.navi_url.trim()
      ? o.navi_url
      : typeof o.place_url === 'string' && o.place_url.trim()
        ? o.place_url
        : `https://map.kakao.com/link/search/${encodeURIComponent(name)}`

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

/**
 * 모델/백엔드가 멀티턴 디버그용으로 붙이는 표식 제거 ([1턴], [AI] 등).
 * 근본 해결은 백엔드에서 깨끗한 `answer`만 내리는 것이 좋고, 프론트는 표시·TTS용으로 보조 정제합니다.
 */
export function sanitizeChatAnswer(text: string): string {
  return text
    .replace(/\[\s*\d+\s*턴\s*\]/gi, '')
    .replace(/\[AI\]/gi, '')
    .replace(/\[USER\]/gi, '')
    .replace(/\[사용자\]/g, '')
    .replace(/\[어시스턴트\]/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
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
  const root = data as Record<string, unknown>

  let hospitals: Hospital[] = []
  const rawH = root.hospitals
  const hospitalList =
    Array.isArray(rawH)
      ? rawH
      : rawH &&
          typeof rawH === 'object' &&
          Array.isArray((rawH as { nearby?: unknown }).nearby)
        ? (rawH as { nearby: unknown[] }).nearby
        : []
  if (hospitalList.length) {
    hospitals = hospitalList
      .map(parseHospitalEntry)
      .filter((h): h is Hospital => h !== null)
  }

  const emergencyRaw = root.emergency
  const legacyIsEmergency = root.is_emergency
  const emergency =
    emergencyRaw === undefined || emergencyRaw === null
      ? typeof legacyIsEmergency === 'boolean'
        ? { is_emergency: legacyIsEmergency, severity: legacyIsEmergency ? 'HIGH' : 'LOW' }
        : null
      : parseEmergency(emergencyRaw)

  const intentRaw = root.intent
  const intent = typeof intentRaw === 'string' ? intentRaw : undefined

  const answerRaw = root.answer
  let cleanedAnswer = ''
  if (typeof answerRaw === 'string') {
    cleanedAnswer = sanitizeChatAnswer(answerRaw)
  } else if (answerRaw != null) {
    cleanedAnswer = sanitizeChatAnswer(String(answerRaw))
  }

  if (!cleanedAnswer) {
    if (intent?.toLowerCase() === 'paging') {
      cleanedAnswer = '다음 병원을 안내해 드릴게요.'
    } else if (emergency?.is_emergency) {
      cleanedAnswer = '응급 상황이에요. 안전을 먼저 확인해 주세요.'
    } else if (hospitals.length > 0) {
      cleanedAnswer = '근처 병원 정보를 찾았어요. 안내해 드릴게요.'
    } else {
      throw new Error('응답에 답변 내용이 없습니다. 잠시 후 다시 시도해 주세요.')
    }
  }

  const ttsRaw =
    root.tts_url ?? root.tts_audio_url ?? root.audio_url ?? root.audio_path
  const ttsUrl =
    typeof ttsRaw === 'string' && /^https?:\/\//i.test(ttsRaw.trim())
      ? ttsRaw.trim()
      : undefined

  const readyRaw = root.ready_for_c
  let ready_for_c: boolean | undefined = typeof readyRaw === 'boolean' ? readyRaw : undefined
  /**
   * Colab `pipeline_integrated` 노트북의 `ChatResponse`는 `ready_for_c`를 생략하는 경우가 많음.
   * `full_pipeline` 본응답은 보통 C팀까지 돌았을 때 병원 목록이 있으면 한 턴 정보 제공 완료로 간주.
   */
  if (ready_for_c === undefined) {
    if (intent?.toLowerCase() === 'paging') {
      ready_for_c = false
    } else if (intent?.toLowerCase() === 'emergency' || emergency?.is_emergency === true) {
      ready_for_c = true
    } else if (hospitals.length > 0) {
      ready_for_c = true
    }
  }

  return {
    answer: cleanedAnswer,
    intent,
    hospitals,
    emergency: emergency ?? undefined,
    ttsUrl,
    ready_for_c,
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
