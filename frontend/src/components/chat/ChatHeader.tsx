import { ASSISTANT_NICKNAME, SERVICE_NAME } from '../../brand'
import { IconSpeaker } from './icons'
import styles from './ChatHeader.module.css'

export function ChatHeader() {
  return (
    <header className={styles.wrap}>
      <div className={styles.iconBox} aria-hidden>
        <IconSpeaker />
      </div>
      <p className={styles.eyebrow}>{SERVICE_NAME}</p>
      <h1 className={styles.title}>어디가 불편하세요?</h1>
      <p className={styles.subtitle}>
        {ASSISTANT_NICKNAME}에게 편하게 말씀해 주세요.
      </p>
    </header>
  )
}
