import { useCallback, useEffect, useMemo, useRef } from 'react'
import { useGeolocation } from '../../hooks/useGeolocation'
import { useMedicalChat } from '../../hooks/useMedicalChat'
import { useWakeWord } from '../../hooks/useWakeWord'
import { ChatCard, ChatCardBody } from './ChatCard'
import { ChatHeader } from './ChatHeader'
import { ChatLayout } from './ChatLayout'
import { ChatMessageList } from './ChatMessageList'
import { HospitalInfoPanel } from './HospitalInfoPanel'
import { ServiceDisclaimer } from './ServiceDisclaimer'
import { VoiceInputPanel } from './VoiceInputPanel'

export function MedicalChatScreen() {
  const { lat, lng } = useGeolocation()
  const { messages, appendUserMessage, isSending } = useMedicalChat({ lat, lng })

  const onVoiceResult = useCallback(
    (text: string) => {
      if (isSending) return
      appendUserMessage(text)
    },
    [appendUserMessage, isSending],
  )

  const {
    listening,
    notice: voiceNotice,
    isContinuousMode,
    beginFollowUpRecording,
  } = useWakeWord(onVoiceResult, { isSending })

  const beginFollowUpRef = useRef(beginFollowUpRecording)
  beginFollowUpRef.current = beginFollowUpRecording
  const isContinuousRef = useRef(isContinuousMode)
  isContinuousRef.current = isContinuousMode
  const isSendingRef = useRef(isSending)
  isSendingRef.current = isSending
  const lastTtsAssistantIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!isContinuousMode) {
      window.speechSynthesis.cancel()
      lastTtsAssistantIdRef.current = null
    }
  }, [isContinuousMode])

  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last || last.role !== 'assistant') return
    if (!isContinuousMode) return
    if (lastTtsAssistantIdRef.current === last.id) return
    lastTtsAssistantIdRef.current = last.id

    const ttsUrl = last.ttsUrl?.trim()
    const playThenListen = () => {
      if (isContinuousRef.current && !isSendingRef.current) {
        beginFollowUpRef.current()
      }
    }

    if (ttsUrl) {
      window.speechSynthesis.cancel()
      const audio = new Audio(ttsUrl)
      audio.onended = playThenListen
      audio.onerror = playThenListen
      void audio.play().catch(playThenListen)
      return () => {
        audio.pause()
        audio.removeAttribute('src')
      }
    }

    window.speechSynthesis.cancel()
    const text = last.content.trim()
    if (!text) {
      window.queueMicrotask(playThenListen)
      return
    }

    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'ko-KR'
    u.onend = playThenListen
    u.onerror = playThenListen
    window.speechSynthesis.speak(u)
    return () => {
      window.speechSynthesis.cancel()
    }
  }, [messages, isContinuousMode])

  const hasChat = messages.length > 0

  const latestHospitals = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]
      if (m.role === 'assistant') {
        return m.hospitals ?? []
      }
    }
    return []
  }, [messages])

  return (
    <ChatLayout
      chat={
        <ChatCard>
          <ChatHeader />
          <ChatCardBody>
            {hasChat && <ChatMessageList messages={messages} />}

            {!hasChat ? (
              <VoiceInputPanel
                listening={listening}
                variant="hero"
                disabled={isSending}
                notice={voiceNotice}
                passive
              />
            ) : (
              <VoiceInputPanel
                listening={listening}
                variant="compact"
                disabled={isSending}
                notice={voiceNotice}
                passive
              />
            )}
          </ChatCardBody>
          <ServiceDisclaimer />
        </ChatCard>
      }
      hospitalInfo={<HospitalInfoPanel hospitals={latestHospitals} />}
    />
  )
}
