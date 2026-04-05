import { IconSpeaker } from './icons'
import styles from './ChatHeader.module.css'

export function ChatHeader() {
  return (
    <header className={styles.wrap}>
      <div className={styles.iconBox} aria-hidden>
        <IconSpeaker />
      </div>
      <h1 className={styles.title}>어디가 불편하세요?</h1>
      <p className={styles.subtitle}>현재 느끼시는 증상을 말씀해주세요</p>
    </header>
  )
}
