import { useCallback, useMemo } from 'react'
import { useGeolocation } from '../../hooks/useGeolocation'
import { useMedicalChat } from '../../hooks/useMedicalChat'
import { useVoiceInput } from '../../hooks/useVoiceInput'
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
      appendUserMessage(text)
    },
    [appendUserMessage],
  )

  const {
    listening,
    start,
    stop,
    voiceError,
    speechSupported,
  } = useVoiceInput(onVoiceResult)

  const voiceNotice =
    voiceError ??
    (!speechSupported
      ? '음성 입력은 Chrome·Microsoft Edge(데스크톱)에서 가장 잘 동작합니다. 마이크 권한을 허용해 주세요.'
      : null)

  const handleMicToggle = () => {
    if (isSending) return
    if (listening) stop()
    else start()
  }

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
                onPress={handleMicToggle}
                variant="hero"
                disabled={isSending}
                notice={voiceNotice}
              />
            ) : (
              <VoiceInputPanel
                listening={listening}
                onPress={handleMicToggle}
                variant="compact"
                disabled={isSending}
                notice={voiceNotice}
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
