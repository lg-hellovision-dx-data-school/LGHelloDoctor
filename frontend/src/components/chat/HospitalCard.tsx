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
      <h3 className={styles.name}>🏥{h.name}</h3>
      <p className={styles.line}>📍{h.address}</p>
      <p className={styles.line}>📞{h.phone}</p>
      <p className={styles.time}>
        🚶 도보 약 {h.walk_time}분
        {h.drive_time != null ? ` / 🚗 차량 약 ${h.drive_time}분` : ''}
      </p>
      <p className={styles.disclaimer}>
        💡 방문 전 병원에 전화하여 영업시간을 꼭 확인해 주세요.
      </p>
      <div className={styles.actions}>
        {tel ? (
          <a className={styles.btnSecondary} href={tel}>
            📞 전화걸기
          </a>
        ) : (
          <span className={`${styles.btnSecondary} ${styles.btnDisabled}`}>
            📞 전화걸기
          </span>
        )}
        <a
          className={styles.btnPrimary}
          href={h.navi_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          🗺️ 카카오맵 길찾기
        </a>
      </div>
    </article>
  )
}
