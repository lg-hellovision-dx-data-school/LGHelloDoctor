import { ASSISTANT_NICKNAME, SERVICE_NAME } from '../../brand'
import styles from './ServiceDisclaimer.module.css'

export function ServiceDisclaimer() {
  return (
    <p className={styles.notice}>
      {SERVICE_NAME}({ASSISTANT_NICKNAME})는 증상에 대한 일반적인 의료 안내를 제공하는
      참고용 정보입니다. 정확한 진단과 치료 결정은 반드시 의사 등 의료진과 상담해
      주세요.
    </p>
  )
}
