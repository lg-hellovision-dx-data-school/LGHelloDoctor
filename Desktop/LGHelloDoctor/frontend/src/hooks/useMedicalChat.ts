import { useCallback, useMemo, useRef, useState } from 'react'
import { postChat } from '../api/chat'
import type { ChatMessage } from '../types/chat'

const SESSION_ID = 'test_01'
const DEFAULT_LAT = 37.5012
const DEFAULT_LNG = 127.0396

function randomId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useMedicalChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const sendingRef = useRef(false)

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
      const answer = await postChat({
        text: trimmed,
        session_id: SESSION_ID,
        lat: DEFAULT_LAT,
        lng: DEFAULT_LNG,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: randomId(),
          role: 'assistant',
          content: answer,
          createdAt: Date.now(),
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

  return useMemo(
    () => ({
      messages,
      appendUserMessage,
      isSending,
      reset,
    }),
    [messages, appendUserMessage, isSending, reset],
  )
}
