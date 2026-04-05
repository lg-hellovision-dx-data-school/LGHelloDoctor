import type { ChatMessage } from '../../types/chat'
import styles from './MessageBubble.module.css'

type Props = {
  message: ChatMessage
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`${styles.row} ${isUser ? styles.rowUser : ''}`}
    >
      <div
        className={`${styles.bubble} ${isUser ? styles.user : styles.assistant}`}
      >
        <span className={styles.label}>
          {isUser ? '나' : '의료 AI'}
        </span>
        {message.content}
      </div>
    </div>
  )
}
