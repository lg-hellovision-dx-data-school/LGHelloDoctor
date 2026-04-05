import { useCallback, useState } from 'react'
import { useMedicalChat } from '../../hooks/useMedicalChat'
import { useVoiceInput } from '../../hooks/useVoiceInput'
import type { InputMode } from '../../types/chat'
import { ChatCard, ChatCardBody } from './ChatCard'
import { ChatHeader } from './ChatHeader'
import { ChatLayout } from './ChatLayout'
import { ChatMessageList } from './ChatMessageList'
import { InputModeToggle } from './InputModeToggle'
import { TextComposer } from './TextComposer'
import { VoiceInputPanel } from './VoiceInputPanel'

export function MedicalChatScreen() {
  const { messages, appendUserMessage, isSending } = useMedicalChat()
  const [mode, setMode] = useState<InputMode>('voice')

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

  return (
    <ChatLayout>
      <ChatCard>
        <ChatHeader />
        <InputModeToggle mode={mode} onChange={setMode} />
        <ChatCardBody>
          {hasChat && <ChatMessageList messages={messages} />}

          {!hasChat && mode === 'voice' && (
            <VoiceInputPanel
              listening={listening}
              onPress={handleMicToggle}
              variant="hero"
              disabled={isSending}
              notice={voiceNotice}
            />
          )}

          {!hasChat && mode === 'text' && (
            <TextComposer
              onSend={appendUserMessage}
              layout="centered"
              disabled={isSending}
            />
          )}

          {hasChat && mode === 'voice' && (
            <VoiceInputPanel
              listening={listening}
              onPress={handleMicToggle}
              variant="compact"
              disabled={isSending}
              notice={voiceNotice}
            />
          )}

          {hasChat && mode === 'text' && (
            <TextComposer
              onSend={appendUserMessage}
              layout="footer"
              disabled={isSending}
            />
          )}
        </ChatCardBody>
      </ChatCard>
    </ChatLayout>
  )
}
