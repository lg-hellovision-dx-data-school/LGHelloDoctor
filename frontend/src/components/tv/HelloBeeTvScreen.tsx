import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useGeolocation } from '../../hooks/useGeolocation'
import { useMedicalChat } from '../../hooks/useMedicalChat'
import { useWakeWord } from '../../hooks/useWakeWord'
import type { ChatMessage, Hospital } from '../../types/chat'
import styles from './HelloBeeTvScreen.module.css'

function firstSentence(text: string): string {
  const t = text.trim()
  if (!t) return ''
  const cut = t.split(/[.。!?]/)[0]?.trim()
  return cut || t.split('\n')[0]?.trim() || t
}

function latestAssistantMessage(msgs: ChatMessage[]): ChatMessage | null {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') return msgs[i]
  }
  return null
}

/** Vite `public/` 기준. 잘못 저장된 `background_video.mp4.mp4` 도 순서대로 시도합니다. */
function tvBackgroundVideoSources(): string[] {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '') || ''
  return [`${base}/background_video.mp4`, `${base}/background_video.mp4.mp4`]
}

export function HelloBeeTvScreen() {
  const { lat, lng } = useGeolocation()
  const { messages, appendUserMessage, isSending, rotateSessionForNewConversation } = useMedicalChat({
    lat,
    lng,
  })
  const videoRef = useRef<HTMLVideoElement>(null)
  const [videoMissing, setVideoMissing] = useState(false)
  const [celebrate, setCelebrate] = useState(false)
  const [isAiSpeaking, setIsAiSpeaking] = useState(false)
  const prevMsgLenRef = useRef(0)
  const lastTtsAssistantIdRef = useRef<string | null>(null)
  const beginFollowUpRef = useRef<() => void>(() => {})
  const exitContinuousRef = useRef<() => void>(() => {})
  const resetIdleTimerRef = useRef<() => void>(() => {})
  const isContinuousRef = useRef(false)
  const isSendingRef = useRef(false)
  const rotateSessionRef = useRef(rotateSessionForNewConversation)
  rotateSessionRef.current = rotateSessionForNewConversation
  const setIdleExitSuspendedRef = useRef<(suspended: boolean) => void>(() => {})

  const onVoiceResult = useCallback(
    (text: string) => {
      if (isSending) return
      appendUserMessage(text)
    },
    [appendUserMessage, isSending],
  )

  const {
    listening,
    notice,
    isContinuousMode,
    beginFollowUpRecording,
    exitContinuousMode,
    resetContinuousIdleTimer,
    setIdleExitSuspended,
    status,
  } = useWakeWord(onVoiceResult, {
    isSending,
    idleExitMs: 6000,
    silenceExitMessage: '어르신, 대답이 없으셔서 잠시 쉬고 있을게요.',
  })

  beginFollowUpRef.current = beginFollowUpRecording
  exitContinuousRef.current = exitContinuousMode
  resetIdleTimerRef.current = resetContinuousIdleTimer
  isContinuousRef.current = isContinuousMode
  isSendingRef.current = isSending
  setIdleExitSuspendedRef.current = setIdleExitSuspended

  useEffect(() => {
    if (!isContinuousMode) {
      setIdleExitSuspendedRef.current(false)
      window.speechSynthesis.cancel()
      lastTtsAssistantIdRef.current = null
      setIsAiSpeaking(false)
    }
  }, [isContinuousMode])

  useEffect(() => {
    const last = messages[messages.length - 1]
    if (!last || last.role !== 'assistant') return
    if (!isContinuousMode) return
    if (lastTtsAssistantIdRef.current === last.id) return
    lastTtsAssistantIdRef.current = last.id

    const playThenListen = () => {
      setIdleExitSuspendedRef.current(false)
      setIsAiSpeaking(false)
      if (!isContinuousRef.current || isSendingRef.current) return
      if (last.ready_for_c === true) {
        rotateSessionRef.current()
        exitContinuousRef.current()
        return
      }
      resetIdleTimerRef.current()
      beginFollowUpRef.current()
    }

    const ttsUrl = last.ttsUrl?.trim()
    if (ttsUrl) {
      window.speechSynthesis.cancel()
      setIdleExitSuspendedRef.current(true)
      setIsAiSpeaking(true)
      const audio = new Audio(ttsUrl)
      audio.onended = playThenListen
      audio.onerror = playThenListen
      void audio.play().catch(playThenListen)
      return () => {
        setIdleExitSuspendedRef.current(false)
        audio.pause()
        audio.removeAttribute('src')
        setIsAiSpeaking(false)
      }
    }

    window.speechSynthesis.cancel()
    const text = last.content.trim()
    if (!text) {
      window.queueMicrotask(playThenListen)
      return
    }

    setIdleExitSuspendedRef.current(true)
    setIsAiSpeaking(true)
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'ko-KR'
    u.onend = playThenListen
    u.onerror = playThenListen
    window.speechSynthesis.speak(u)
    return () => {
      setIdleExitSuspendedRef.current(false)
      window.speechSynthesis.cancel()
      setIsAiSpeaking(false)
    }
  }, [messages, isContinuousMode])

  useEffect(() => {
    const last = messages[messages.length - 1]
    if (last?.role === 'user' && messages.length > prevMsgLenRef.current) {
      setCelebrate(true)
      const t = window.setTimeout(() => setCelebrate(false), 2000)
      prevMsgLenRef.current = messages.length
      return () => window.clearTimeout(t)
    }
    prevMsgLenRef.current = messages.length
  }, [messages])

  const assistantLatest = useMemo(() => latestAssistantMessage(messages), [messages])

  const emergencyActive = useMemo(
    () =>
      Boolean(
        assistantLatest &&
          (assistantLatest.intent?.toLowerCase() === 'emergency' ||
            assistantLatest.emergency?.is_emergency),
      ),
    [assistantLatest],
  )

  const hospitalsToShow = useMemo(() => {
    const list = assistantLatest?.hospitals
    if (!Array.isArray(list) || list.length === 0) return []
    return list
      .filter(
        (h) =>
          h != null &&
          typeof h === 'object' &&
          typeof (h as Hospital).name === 'string' &&
          (h as Hospital).name.trim().length > 0,
      )
      .slice(0, 3) as Hospital[]
  }, [assistantLatest])

  useEffect(() => {
    const v = videoRef.current
    if (!v || videoMissing) return
    if (emergencyActive) {
      v.pause()
    } else {
      void v.play().catch(() => {
        /* autoplay 정책 등 */
      })
    }
  }, [emergencyActive, videoMissing])

  const drawerOpen =
    isContinuousMode ||
    status === 'recording' ||
    status === 'uploading' ||
    messages.length > 0

  const talking = (listening || isAiSpeaking) && !emergencyActive
  const faceEmoji = talking ? '😮' : '🙂'

  const headline = useMemo(() => {
    if (hospitalsToShow.length > 0) {
      const hint = firstSentence(assistantLatest?.content ?? '')
      return hint || '가까운 병원을 안내해 드려요'
    }
    return firstSentence(assistantLatest?.content ?? '') || '헬로비가 도와드릴게요'
  }, [assistantLatest, hospitalsToShow.length])

  const showMicInDrawer =
    listening || status === 'recording' || status === 'uploading'

  const drawerBubbleText = useMemo(() => {
    if (listening || status === 'recording' || status === 'uploading') {
      return notice
    }
    if (isSending && !assistantLatest?.content?.trim()) {
      return '답변을 준비하고 있어요. 잠시만 기다려 주세요.'
    }
    const answer = assistantLatest?.content?.trim()
    if (answer) return answer
    if (isContinuousMode) return notice
    return '말씀해 주세요.'
  }, [listening, status, notice, isSending, assistantLatest, isContinuousMode])

  return (
    <div className={styles.root}>
      <div className={styles.pageChrome}>
        <a className={styles.backToChat} href={import.meta.env.BASE_URL}>
          일반 채팅 화면으로
        </a>
      </div>

      <div className={styles.tvStage}>
        <div className={styles.tvBezel} aria-label="TV 16 대 9 시연 화면">
          <div className={styles.tvScreen}>
            {!videoMissing ? (
              <video
                ref={videoRef}
                className={styles.bgVideo}
                autoPlay
                loop
                muted
                playsInline
                aria-hidden
                onError={() => setVideoMissing(true)}
              >
                {tvBackgroundVideoSources().map((src) => (
                  <source key={src} src={src} type="video/mp4" />
                ))}
              </video>
            ) : (
              <div className={styles.bgFallback} aria-hidden />
            )}

            <div className={styles.layerUi}>
              {emergencyActive && (
                <div className={styles.emergencyLayer} role="alert" aria-live="assertive">
                  <div className={styles.emergencyBox}>
                    <p className={styles.emergencyTitle}>119에 연결 중입니다</p>
                    <p className={styles.emergencySub}>응급 상황입니다. 잠시만 기다려 주세요.</p>
                  </div>
                </div>
              )}

              {!drawerOpen && (
                <div className={styles.idleBubbleWrap} role="status" aria-label="호출 안내">
                  <div className={styles.idleFace} aria-hidden>
                    <span className={styles.idleFaceEmoji}>🙂</span>
                  </div>
                  <div className={styles.speechBubble}>
                    <p className={styles.speechBubbleText}>
                      몸이 불편하실 땐
                      <br />
                      <span className={styles.idleHintAccent}>&ldquo;헬로비~&rdquo;</span>를 불러주세요!
                    </p>
                  </div>
                </div>
              )}

              <aside
                className={`${styles.drawer} ${drawerOpen ? '' : styles.drawerHidden}`}
                aria-label="헬로비 TV 안내"
                aria-hidden={!drawerOpen}
              >
                <div className={styles.drawerInner}>
                  <div className={styles.charRow}>
                    <div
                      className={`${styles.character} ${talking ? styles.characterTalking : ''} ${celebrate ? styles.characterCelebrate : ''}`}
                      aria-hidden
                    >
                      <span>{faceEmoji}</span>
                      <span className={styles.sparkles} />
                    </div>
                    <div className={styles.drawerBubbleColumn}>
                      <div
                        className={styles.drawerSpeechBubble}
                        role="status"
                        aria-live="polite"
                        aria-atomic="true"
                      >
                        {showMicInDrawer && (
                          <span className={styles.drawerMic} aria-hidden>
                            🎤
                          </span>
                        )}
                        <p className={styles.drawerBubbleText}>{drawerBubbleText}</p>
                      </div>
                    </div>
                  </div>

                  {hospitalsToShow.length > 0 ? (
                    <div className={styles.mainPanel}>
                      <HospitalTvGrid hospitals={hospitalsToShow} introLine={headline} />
                    </div>
                  ) : null}
                </div>
              </aside>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatWalkMinutes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return '—'
  return String(Math.round(n))
}

function HospitalTvGrid({ hospitals, introLine }: { hospitals: Hospital[]; introLine: string }) {
  const list = hospitals.slice(0, 3)
  if (list.length === 0) return null

  return (
    <div className={styles.hospitalPanel}>
      <p className={styles.hospitalIntro}>{introLine}</p>
      <p className={styles.hospitalVoiceHint} role="note">
        <span className={styles.hospitalVoiceHintAccent}>안내:</span> 가까운 병원을 최대 세 곳까지
        한눈에 보여 드려요. 더 물어보실 내용은 &quot;헬로비~&quot;를 불러 주세요.
      </p>

      <div className={styles.hospitalCardsRow}>
        {list.map((h, i) => (
          <HospitalMiniCard key={`${h.name}-${i}`} hospital={h} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}

function HospitalMiniCard({ hospital: h, rank }: { hospital: Hospital; rank: number }) {
  const name = String(h.name ?? '').trim() || '이름 미상'
  const address = String(h.address ?? '').trim() || '주소 정보 없음'
  const phone = String(h.phone ?? '').trim() || '—'
  const walk = formatWalkMinutes(Number(h.walk_time))

  return (
    <article className={styles.hospitalMiniCard}>
      <h3 className={styles.hospitalMiniName}>
        <span className={styles.hospitalMiniRank}>{rank}. </span>
        {name}
      </h3>
      <p className={styles.hospitalMiniLine}>
        <span className={styles.hospitalMiniLabel}>주소</span> {address}
      </p>
      <p className={styles.hospitalMiniLine}>
        <span className={styles.hospitalMiniLabel}>도보</span> 약 {walk}분
      </p>
      <p className={styles.hospitalMiniPhone}>
        <span className={styles.hospitalMiniLabel}>전화</span> {phone}
      </p>
      <p className={styles.hospitalMiniHint} role="note">
        방문 전 <span className={styles.accentStrong}>영업시간</span>은 전화로 꼭 확인해 주세요.
      </p>
    </article>
  )
}
