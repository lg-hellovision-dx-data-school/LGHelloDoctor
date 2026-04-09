const DEFAULT_API_BASE = 'http://localhost:8000'

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function inferBaseFromChatUrl(chatUrl: string): string | null {
  const trimmed = chatUrl.trim()
  if (!/^https?:\/\//i.test(trimmed)) return null
  return trimmed.replace(/\/chat\/?$/i, '')
}

export function getApiBaseUrl(): string {
  const envBase = import.meta.env.VITE_API_URL?.trim()
  if (envBase && /^https?:\/\//i.test(envBase)) {
    return trimTrailingSlash(envBase)
  }

  const envChat = import.meta.env.VITE_CHAT_API_URL?.trim()
  if (envChat) {
    const inferred = inferBaseFromChatUrl(envChat)
    if (inferred) return trimTrailingSlash(inferred)
  }

  return DEFAULT_API_BASE
}

export function getSttApiUrl(): string {
  return `${getApiBaseUrl()}/api/stt`
}

type SttSuccessResponse = {
  text?: unknown
  status?: unknown
  detail?: unknown
}

export async function postSttAudio(audioBlob: Blob): Promise<string> {
  const form = new FormData()
  form.append('audio', audioBlob, 'wake-word.wav')

  let res: Response
  try {
    res = await fetch(getSttApiUrl(), {
      method: 'POST',
      body: form,
      headers: {
        'ngrok-skip-browser-warning': '69420',
      },
    })
  } catch {
    throw new Error('음성 서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.')
  }

  let data: SttSuccessResponse | null = null
  try {
    data = (await res.json()) as SttSuccessResponse
  } catch {
    if (!res.ok) {
      throw new Error(`음성 처리 요청이 실패했습니다 (${res.status}).`)
    }
    throw new Error('음성 인식 응답을 해석할 수 없습니다.')
  }

  if (!res.ok) {
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      throw new Error(data.detail.trim())
    }
    throw new Error(`음성 처리 요청이 실패했습니다 (${res.status}).`)
  }

  const text = typeof data?.text === 'string' ? data.text.trim() : ''
  if (!text) {
    throw new Error('음성 인식 결과가 비어 있습니다. 다시 시도해 주세요.')
  }
  return text
}
