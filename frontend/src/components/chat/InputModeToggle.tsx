import type { InputMode } from '../../types/chat'
import { IconKeyboard, IconMic } from './icons'
import styles from './InputModeToggle.module.css'

type Props = {
  mode: InputMode
  onChange: (mode: InputMode) => void
}

export function InputModeToggle({ mode, onChange }: Props) {
  return (
    <div className={styles.row} role="tablist" aria-label="입력 방식 선택">
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'voice'}
        className={`${styles.btn} ${mode === 'voice' ? styles.active : styles.inactive}`}
        onClick={() => onChange('voice')}
      >
        <IconMic />
        음성 입력
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'text'}
        className={`${styles.btn} ${mode === 'text' ? styles.active : styles.inactive}`}
        onClick={() => onChange('text')}
      >
        <IconKeyboard />
        텍스트 입력
      </button>
    </div>
  )
}
