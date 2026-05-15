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
      <header className={styles.header}>
        <h2 className={styles.title}>가까운 병원</h2>
        {hasList ? (
          <span className={styles.count} aria-label={`${hospitals.length}곳`}>
            {hospitals.length}곳
          </span>
        ) : null}
      </header>
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
          <div className={styles.placeholder}>
            <p className={styles.placeholderTitle}>아직 안내된 병원이 없어요</p>
            <p className={styles.placeholderHint}>
              증상을 말씀해 주시면<br />주변 병원을 찾아드릴게요.
            </p>
          </div>
        )}
      </div>
    </aside>
  )
}
