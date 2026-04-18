import type { ReactNode } from 'react'
import styles from './ChatLayout.module.css'

type Props = {
  /** 좌측: 채팅 카드 영역 */
  chat: ReactNode
  /** 우측: 병원 정보 패널 */
  hospitalInfo: ReactNode
}

export function ChatLayout({ chat, hospitalInfo }: Props) {
  return (
    <div className={styles.page}>
      <div className={styles.split}>
        <div className={styles.chatPane}>{chat}</div>
        <div className={styles.hospitalPane}>{hospitalInfo}</div>
      </div>
    </div>
  )
}
