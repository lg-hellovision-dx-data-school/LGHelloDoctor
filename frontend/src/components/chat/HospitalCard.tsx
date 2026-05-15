import type { Hospital } from '../../types/chat'
import styles from './HospitalCard.module.css'

type Props = {
  hospital: Hospital
}

function telHref(phone: string): string | null {
  const digits = phone.replace(/[^\d+]/g, '')
  return digits ? `tel:${digits}` : null
}

export function HospitalCard({ hospital: h }: Props) {
  const tel = telHref(h.phone)

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <span className={styles.icon} aria-hidden>🏥</span>
        <h3 className={styles.name}>{h.name}</h3>
      </header>

      <dl className={styles.meta}>
        <div className={styles.metaRow}>
          <dt className={styles.metaIcon} aria-hidden>📍</dt>
          <dd className={styles.metaValue}>{h.address}</dd>
        </div>
        <div className={styles.metaRow}>
          <dt className={styles.metaIcon} aria-hidden>📞</dt>
          <dd className={styles.metaValue}>{h.phone}</dd>
        </div>
        <div className={styles.metaRow}>
          <dt className={styles.metaIcon} aria-hidden>🚶</dt>
          <dd className={styles.metaValue}>
            도보 약 <strong>{h.walk_time}분</strong>
            {h.drive_time != null ? (
              <>
                <span className={styles.metaSep} aria-hidden>·</span>
                🚗 차량 약 <strong>{h.drive_time}분</strong>
              </>
            ) : null}
          </dd>
        </div>
      </dl>

      <p className={styles.disclaimer}>
        💡 방문 전 영업시간을 꼭 확인해 주세요.
      </p>

      <div className={styles.actions}>
        {tel ? (
          <a className={styles.btnSecondary} href={tel}>
            전화 걸기
          </a>
        ) : (
          <span className={`${styles.btnSecondary} ${styles.btnDisabled}`}>
            전화 걸기
          </span>
        )}
        <a
          className={styles.btnPrimary}
          href={h.navi_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          길찾기
        </a>
      </div>
    </article>
  )
}
