import type { Hospital } from '../../types/chat'
import { HospitalCard } from './HospitalCard'
import styles from './HospitalInfoPanel.module.css'

type Props = {
  hospitals: Hospital[]
}

export function HospitalInfoPanel({ hospitals }: Props) {
  const hasList = hospitals.length > 0

  return (
    <aside className={styles.panel} aria-label="주변 병원 안내">
      <h2 className={styles.title}>주변 병원</h2>
      <div className={styles.scroll}>
        {hasList ? (
          <ul className={styles.list}>
            {hospitals.map((h) => (
              <li key={`${h.name}-${h.navi_url}`}>
                <HospitalCard hospital={h} />
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.placeholder}>현재 안내된 병원이 없습니다.</p>
        )}
      </div>
    </aside>
  )
}
