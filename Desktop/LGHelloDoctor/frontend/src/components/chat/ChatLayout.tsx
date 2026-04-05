import type { ReactNode } from 'react'
import styles from './ChatLayout.module.css'

type Props = {
  children: ReactNode
}

export function ChatLayout({ children }: Props) {
  return (
    <div className={styles.page}>
      <div className={styles.inner}>{children}</div>
    </div>
  )
}
