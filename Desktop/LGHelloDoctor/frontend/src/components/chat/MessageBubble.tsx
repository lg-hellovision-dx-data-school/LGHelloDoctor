import { ASSISTANT_NICKNAME } from '../../brand'
import type { ChatMessage } from '../../types/chat'
import styles from './MessageBubble.module.css'

type Props = {
  message: ChatMessage
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const showEmergency =
    !isUser &&
    message.emergency?.is_emergency &&
    message.emergency.severity === 'HIGH'

  return (
    <div
      className={`${styles.row} ${isUser ? styles.rowUser : ''}`}
    >
      <div
        className={
          isUser ? undefined : styles.assistantColumn
        }
      >
        {showEmergency ? (
          <p className={styles.emergencyBanner} role="status">
            응급 증상이 의심됩니다. 즉시 119에 연락하거나 가까운 응급실로 가시기 바랍니다.
          </p>
        ) : null}
        <div
          className={`${styles.bubble} ${isUser ? styles.user : styles.assistant}`}
        >
          <span className={styles.label}>
            {isUser ? '나' : ASSISTANT_NICKNAME}
          </span>
          {message.content}
        </div>
      </div>
    </div>
  )
}
