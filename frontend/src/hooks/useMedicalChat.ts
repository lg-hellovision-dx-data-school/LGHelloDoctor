import { useCallback, useMemo, useRef, useState } from 'react'
import { postChat } from '../api/chat'
import type { ChatMessage } from '../types/chat'

const SESSION_KEY = 'lghellodoctor_session_id'

function randomId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function getOrCreateSessionId(): string {
  const fallback = `web-${randomId()}`
  if (typeof window === 'undefined') return fallback
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY)?.trim()
    if (existing) return existing
    window.sessionStorage.setItem(SESSION_KEY, fallback)
    return fallback
  } catch {
    return fallback
  }
}

type GeoCoords = { lat: number; lng: number }

export function useMedicalChat(coords: GeoCoords) {
  const sessionIdRef = useRef(getOrCreateSessionId())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const sendingRef = useRef(false)
  const coordsRef = useRef(coords)
  coordsRef.current = coords

  const appendUserMessage = useCallback(async (content: string) => {
    const trimmed = content.trim()
    if (!trimmed || sendingRef.current) return

    sendingRef.current = true
    setIsSending(true)

    const userMsg: ChatMessage = {
      id: randomId(),
      role: 'user',
      content: trimmed,
      createdAt: Date.now(),
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const { lat, lng } = coordsRef.current
      const res = await postChat({
        text: trimmed,
        session_id: sessionIdRef.current,
        lat,
        lng,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: randomId(),
          role: 'assistant',
          content: res.answer,
          createdAt: Date.now(),
          hospitals:
            Array.isArray(res.hospitals) && res.hospitals.length > 0 ? res.hospitals : undefined,
          emergency: res.emergency ?? null,
          intent: res.intent,
          ttsUrl: res.ttsUrl,
          ready_for_c: res.ready_for_c,
        } satisfies ChatMessage,
      ])
    } catch (err) {
      const detail =
        err instanceof Error
          ? err.message
          : '알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
      setMessages((prev) => [
        ...prev,
        {
          id: randomId(),
          role: 'assistant',
          content: detail,
          createdAt: Date.now(),
        } satisfies ChatMessage,
      ])
    } finally {
      sendingRef.current = false
      setIsSending(false)
    }
  }, [])

  const reset = useCallback(() => {
    setMessages([])
  }, [])

  /** `ready_for_c: true`로 한 턴이 끝난 뒤, 다음 호출어부터는 새 세션으로 `/chat`에 보냅니다. */
  const rotateSessionForNewConversation = useCallback(() => {
    const next = `web-${randomId()}`
    sessionIdRef.current = next
    try {
      window.sessionStorage.setItem(SESSION_KEY, next)
    } catch {
      /* noop */
    }
  }, [])

  return useMemo(
    () => ({
      messages,
      appendUserMessage,
      isSending,
      reset,
      rotateSessionForNewConversation,
    }),
    [messages, appendUserMessage, isSending, reset, rotateSessionForNewConversation],
  )
}
