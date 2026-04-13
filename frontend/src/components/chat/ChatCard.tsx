import type { ReactNode } from 'react'
import styles from './ChatCard.module.css'

type Props = {
  children: ReactNode
}

export function ChatCard({ children }: Props) {
  return <section className={styles.card}>{children}</section>
}

export function ChatCardBody({ children }: Props) {
  return <div className={styles.body}>{children}</div>
}
