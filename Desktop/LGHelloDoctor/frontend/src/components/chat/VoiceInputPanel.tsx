import { ASSISTANT_NICKNAME } from '../../brand'
import { IconMic } from './icons'
import styles from './VoiceInputPanel.module.css'

type Props = {
  listening: boolean
  onPress?: () => void
  variant?: 'hero' | 'compact'
  disabled?: boolean
  passive?: boolean
  /** 음성 인식 안내·오류 메시지 */
  notice?: string | null
}

export function VoiceInputPanel({
  listening,
  onPress,
  variant = 'hero',
  disabled = false,
  passive = false,
  notice,
}: Props) {
  const buttonDisabled = disabled || passive || !onPress
  const idleHint = passive
    ? `${ASSISTANT_NICKNAME} 호출어를 기다리는 중입니다. "헬로비"라고 불러주세요.`
    : `${ASSISTANT_NICKNAME}에게 마이크를 눌러 증상을 말씀해 주세요.`

  if (variant === 'compact') {
    return (
      <div className={styles.compactWrap}>
        {notice ? (
          <p className={styles.notice} role="status">
            {notice}
          </p>
        ) : null}
        <div className={styles.compactRow}>
          <button
            type="button"
            className={`${styles.compactMic} ${listening ? styles.listening : ''}`}
            onClick={() => {
              if (!buttonDisabled && onPress) onPress()
            }}
            disabled={buttonDisabled}
            aria-pressed={listening}
            aria-label={passive ? '호출어 자동 감지 상태' : listening ? '음성 입력 중지' : '음성 입력 시작'}
          >
            <IconMic />
          </button>
        </div>
        <p className={styles.compactHint}>
          {disabled
            ? `${ASSISTANT_NICKNAME} 응답을 기다리는 중입니다.`
            : listening
              ? '듣고 있어요. 말씀이 끝나면 잠시만 기다려 주세요.'
              : idleHint}
        </p>
      </div>
    )
  }

  return (
    <div className={styles.wrap}>
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}
      <button
        type="button"
        className={`${styles.micOuter} ${listening ? styles.listening : ''}`}
        onClick={() => {
          if (!buttonDisabled && onPress) onPress()
        }}
        disabled={buttonDisabled}
        aria-pressed={listening}
        aria-label={passive ? '호출어 자동 감지 상태' : listening ? '음성 입력 중지' : '음성 입력 시작'}
      >
        <IconMic />
      </button>
      <p className={styles.hint}>
        {disabled
          ? `${ASSISTANT_NICKNAME} 응답을 기다리는 중입니다.`
          : listening
            ? '듣고 있습니다. 증상을 천천히 말씀해 주세요.'
            : idleHint}
      </p>
    </div>
  )
}
