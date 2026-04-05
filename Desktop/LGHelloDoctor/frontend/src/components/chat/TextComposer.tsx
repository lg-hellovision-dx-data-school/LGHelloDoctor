import { type FormEvent, useState } from 'react'
import { IconSend } from './icons'
import styles from './TextComposer.module.css'

type Props = {
  onSend: (text: string) => void | Promise<void>
  layout?: 'centered' | 'footer'
  disabled?: boolean
}

export function TextComposer({
  onSend,
  layout = 'centered',
  disabled = false,
}: Props) {
  const [value, setValue] = useState('')

  const submit = async () => {
    const t = value.trim()
    if (!t || disabled) return
    await Promise.resolve(onSend(t))
    setValue('')
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit()
  }

  const formClass =
    layout === 'centered'
      ? `${styles.form} ${styles.formCenter}`
      : `${styles.form} ${styles.footer}`

  return (
    <form className={formClass} onSubmit={onSubmit}>
      <p className={styles.hint}>
        증상을 적어 주시면 AI가 도와드립니다. 전송은 버튼을 눌러 주세요.
      </p>
      <div className={styles.row}>
        <label htmlFor="symptom-text" className="visually-hidden">
          증상 입력
        </label>
        <textarea
          id="symptom-text"
          className={styles.field}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="예: 어제부터 가슴이 답답해요"
          rows={layout === 'footer' ? 2 : 4}
          aria-label="증상 텍스트 입력"
          disabled={disabled}
        />
        <button
          type="submit"
          className={styles.send}
          aria-label="증상 전송"
          disabled={!value.trim() || disabled}
        >
          <IconSend />
        </button>
      </div>
    </form>
  )
}
