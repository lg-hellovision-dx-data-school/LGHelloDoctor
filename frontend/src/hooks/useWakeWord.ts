import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { postSttAudio } from '../api/stt'

type SpeechRecognitionResultLike = {
  0: { transcript: string }
  isFinal: boolean
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: ArrayLike<SpeechRecognitionResultLike>
}

type SpeechRecognitionErrorEventLike = {
  error: string
}

type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null
  onerror: ((ev: SpeechRecognitionErrorEventLike) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/\s+/g, '')
}

function containsWakeWord(text: string, wakeWords: string[]): boolean {
  const normalized = normalizeText(text)
  return wakeWords.some((w) => normalized.includes(normalizeText(w)))
}

const EXIT_PHRASES = [
  '고마워',
  '고맙습니다',
  '감사합니다',
  '잘가',
  '잘 가',
  '종료',
  '끝',
  '그만',
  'bye',
]

function shouldExitContinuousMode(text: string): boolean {
  const n = normalizeText(text)
  return EXIT_PHRASES.some((p) => n.includes(normalizeText(p)))
}

function mapSpeechError(code: string): string | null {
  switch (code) {
    case 'aborted':
      return null
    case 'not-allowed':
      return '마이크 사용 권한이 거부되었습니다. 브라우저 설정에서 마이크를 허용해 주세요.'
    case 'audio-capture':
      return '마이크를 찾을 수 없습니다. 장치 연결 상태를 확인해 주세요.'
    case 'network':
      return '호출어 감지용 음성 인식 네트워크에 연결할 수 없습니다.'
    default:
      return `호출어 감지 오류: ${code}`
  }
}

type WakeStatus = 'idle' | 'armed' | 'recording' | 'uploading'

type HookOptions = {
  durationMs?: number
  wakeWords?: string[]
  /** 말이 없을 때 이 시간(초과) 후 녹음 종료 후 전송 */
  silenceStopMs?: number
  /** 연속 모드: 이 시간 동안 사용자 발화 없으면 연속 모드 해제 */
  idleExitMs?: number
  /** 연속 모드 유휴 종료 직전 TTS 안내(예: TV 6초 침묵). 없으면 바로 종료만 함 */
  silenceExitMessage?: string
  /** 채팅 전송 중에는 후속 녹음 시작 금지 */
  isSending?: boolean
}

const DEFAULT_WAKE_WORDS = ['헬로비', '헬로 비', '헬로비야', 'hello b', 'hello be']

const RMS_THRESHOLD = 18
const MIN_RECORD_BEFORE_SILENCE_MS = 450

async function recordWithVad(
  stream: MediaStream,
  recorder: MediaRecorder,
  opts: { maxMs: number; silenceMs: number },
): Promise<void> {
  const audioContext = new AudioContext()
  const source = audioContext.createMediaStreamSource(stream)
  const analyser = audioContext.createAnalyser()
  analyser.fftSize = 512
  source.connect(analyser)

  const startTime = Date.now()
  let lastVoiceTime = startTime

  const tick = () => {
    const data = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteTimeDomainData(data)
    let sum = 0
    for (let i = 0; i < data.length; i++) {
      const x = data[i] - 128
      sum += x * x
    }
    const rms = Math.sqrt(sum / data.length)
    if (rms > RMS_THRESHOLD) {
      lastVoiceTime = Date.now()
    }
  }

  const waitStop = new Promise<void>((resolve) => {
    recorder.onstop = () => resolve()
  })

  recorder.start(100)
  const interval = window.setInterval(() => {
    tick()
    const elapsed = Date.now() - startTime
    const silentFor = Date.now() - lastVoiceTime
    if (elapsed >= MIN_RECORD_BEFORE_SILENCE_MS && silentFor >= opts.silenceMs) {
      if (recorder.state !== 'inactive') recorder.stop()
    }
    if (elapsed >= opts.maxMs) {
      if (recorder.state !== 'inactive') recorder.stop()
    }
  }, 100)

  await waitStop
  window.clearInterval(interval)
  source.disconnect()
  await audioContext.close().catch(() => {
    /* noop */
  })
}

export function useWakeWord(
  onTranscript: (text: string) => void,
  options?: HookOptions,
) {
  const durationMs = options?.durationMs ?? 7000
  const silenceStopMs = options?.silenceStopMs ?? 5000
  const idleExitMs = options?.idleExitMs ?? 30_000
  const silenceExitMessage = options?.silenceExitMessage
  const wakeWords = options?.wakeWords ?? DEFAULT_WAKE_WORDS
  const isSending = options?.isSending ?? false

  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [status, setStatus] = useState<WakeStatus>('idle')
  const [isContinuousMode, setIsContinuousMode] = useState(false)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const wasContinuousRef = useRef(false)
  const isMountedRef = useRef(true)
  const isRecordingRef = useRef(false)
  const onTranscriptRef = useRef(onTranscript)
  const statusRef = useRef<WakeStatus>('idle')
  const isContinuousModeRef = useRef(false)
  const isSendingRef = useRef(isSending)
  const lastUserActivityRef = useRef(Date.now())
  /** true이면 연속 모드 유휴 타이머로 exitContinuousMode 하지 않음 (AI TTS 재생 중 등) */
  const idleExitSuspendedRef = useRef(false)
  const idleExitSpokenRef = useRef(false)
  const silenceExitMessageRef = useRef<string | undefined>(undefined)
  silenceExitMessageRef.current = silenceExitMessage

  onTranscriptRef.current = onTranscript
  statusRef.current = status
  isContinuousModeRef.current = isContinuousMode
  isSendingRef.current = isSending

  useEffect(() => {
    isContinuousModeRef.current = isContinuousMode
  }, [isContinuousMode])

  useEffect(() => {
    isSendingRef.current = isSending
  }, [isSending])

  const stopRecognition = useCallback(() => {
    const rec = recognitionRef.current
    if (!rec) return
    try {
      rec.onresult = null
      rec.onerror = null
      rec.onend = null
      rec.stop()
    } catch {
      // noop
    }
    recognitionRef.current = null
  }, [])

  const stopStream = useCallback(() => {
    const stream = streamRef.current
    if (!stream) return
    stream.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const beginArmedState = useCallback(() => {
    if (!isMountedRef.current) return
    if (isContinuousModeRef.current) {
      setStatus('armed')
      return
    }
    setStatus('armed')
  }, [])

  const exitContinuousMode = useCallback(() => {
    idleExitSuspendedRef.current = false
    idleExitSpokenRef.current = false
    setIsContinuousMode(false)
    isContinuousModeRef.current = false
  }, [])

  /** AI 답변 직후 마이크 대기 시작 시점부터 유휴 타이머 리셋 */
  const resetContinuousIdleTimer = useCallback(() => {
    lastUserActivityRef.current = Date.now()
    idleExitSpokenRef.current = false
  }, [])

  const setIdleExitSuspended = useCallback((suspended: boolean) => {
    idleExitSuspendedRef.current = suspended
  }, [])

  const recordAndSend = useCallback(async () => {
    if (isRecordingRef.current) return
    isRecordingRef.current = true
    setVoiceError(null)
    setStatus('recording')
    lastUserActivityRef.current = Date.now()
    idleExitSpokenRef.current = false

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
    } catch {
      setVoiceError('마이크 권한이 필요합니다. 브라우저에서 마이크 권한을 허용해 주세요.')
      isRecordingRef.current = false
      beginArmedState()
      return
    }

    const chunks: BlobPart[] = []
    const recorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : undefined,
    })

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) chunks.push(event.data)
    }

    await recordWithVad(stream, recorder, {
      maxMs: durationMs,
      silenceMs: silenceStopMs,
    })
    stopStream()

    try {
      setStatus('uploading')
      const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
      if (blob.size < 256) {
        isRecordingRef.current = false
        beginArmedState()
        return
      }
      const text = (await postSttAudio(blob)).trim()
      if (shouldExitContinuousMode(text)) {
        exitContinuousMode()
      }
      if (text) {
        lastUserActivityRef.current = Date.now()
        idleExitSpokenRef.current = false
        onTranscriptRef.current(text)
      }
      setVoiceError(null)
    } catch (e) {
      setVoiceError(
        e instanceof Error ? e.message : '음성 전송 중 문제가 발생했습니다. 다시 시도해 주세요.',
      )
    } finally {
      isRecordingRef.current = false
      beginArmedState()
    }
  }, [beginArmedState, durationMs, exitContinuousMode, silenceStopMs, stopStream])

  const beginFollowUpRecording = useCallback(() => {
    if (!isContinuousModeRef.current) return
    if (isSendingRef.current) return
    if (isRecordingRef.current) return
    if (document.visibilityState !== 'visible') return
    void recordAndSend()
  }, [recordAndSend])

  const startRecognition = useCallback(() => {
    if (isContinuousModeRef.current) return
    if (document.visibilityState !== 'visible') {
      setStatus('idle')
      return
    }
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) {
      setVoiceError(
        '호출어 감지는 Chrome/Edge 데스크톱에서 지원됩니다. 지원 브라우저를 사용해 주세요.',
      )
      setStatus('idle')
      return
    }

    setVoiceError(null)
    const rec = new Ctor()
    rec.lang = 'ko-KR'
    rec.continuous = true
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onresult = (event: SpeechRecognitionEventLike) => {
      if (isRecordingRef.current) return
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i]?.[0]?.transcript ?? ''
        if (text && containsWakeWord(text, wakeWords)) {
          idleExitSpokenRef.current = false
          setIsContinuousMode(true)
          isContinuousModeRef.current = true
          lastUserActivityRef.current = Date.now()
          void recordAndSend()
          break
        }
      }
    }

    rec.onerror = (event: SpeechRecognitionErrorEventLike) => {
      const msg = mapSpeechError(event.error)
      if (msg) setVoiceError(msg)
    }

    rec.onend = () => {
      recognitionRef.current = null
      if (!isMountedRef.current) return
      if (document.visibilityState !== 'visible') {
        setStatus('idle')
        return
      }
      if (isContinuousModeRef.current) return
      if (statusRef.current === 'recording' || statusRef.current === 'uploading') {
        return
      }
      window.setTimeout(() => {
        if (
          isMountedRef.current &&
          !recognitionRef.current &&
          !isRecordingRef.current &&
          !isContinuousModeRef.current
        ) {
          startRecognition()
        }
      }, 400)
    }

    recognitionRef.current = rec
    rec.start()
    beginArmedState()
  }, [beginArmedState, recordAndSend, wakeWords])

  useEffect(() => {
    isMountedRef.current = true

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        if (!isContinuousModeRef.current && !recognitionRef.current && !isRecordingRef.current) {
          startRecognition()
        }
      } else {
        stopRecognition()
        if (!isRecordingRef.current) setStatus('idle')
      }
    }

    if (!isContinuousModeRef.current) {
      startRecognition()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      isMountedRef.current = false
      document.removeEventListener('visibilitychange', onVisibilityChange)
      stopRecognition()
      stopStream()
    }
  }, [startRecognition, stopRecognition, stopStream])

  useEffect(() => {
    if (isContinuousMode) {
      wasContinuousRef.current = true
      stopRecognition()
      return
    }
    if (wasContinuousRef.current) {
      wasContinuousRef.current = false
      window.setTimeout(() => {
        if (
          isMountedRef.current &&
          !isContinuousModeRef.current &&
          !recognitionRef.current &&
          !isRecordingRef.current &&
          document.visibilityState === 'visible'
        ) {
          startRecognition()
        }
      }, 300)
    }
  }, [isContinuousMode, startRecognition, stopRecognition])

  useEffect(() => {
    const id = window.setInterval(() => {
      if (!isContinuousModeRef.current) return
      if (idleExitSuspendedRef.current) return
      if (Date.now() - lastUserActivityRef.current > idleExitMs) {
        exitContinuousMode()
        window.speechSynthesis.cancel()
      }
    }, 1000)
    return () => window.clearInterval(id)
  }, [exitContinuousMode, idleExitMs])

  const notice = useMemo(() => {
    if (voiceError) return voiceError
    if (isContinuousMode) {
      switch (status) {
        case 'recording':
          return '헬로비가 듣고 있어요… 말씀해 주세요.'
        case 'uploading':
          return '음성을 분석 중입니다. 잠시만 기다려 주세요.'
        default:
          return '말씀해 주세요. 호출어 없이 이어서 대화할 수 있어요.'
      }
    }
    switch (status) {
      case 'recording':
        return '네, 듣고 있어요! 말씀해 주세요.'
      case 'uploading':
        return '음성을 분석 중입니다. 잠시만 기다려 주세요.'
      case 'armed':
        return '호출어 대기 중입니다. "헬로비" 또는 "Hello B"라고 불러주세요.'
      default:
        return '탭이 활성화되면 호출어 감지가 자동으로 시작됩니다.'
    }
  }, [isContinuousMode, status, voiceError])

  return useMemo(
    () => ({
      listening: status === 'recording',
      status,
      notice,
      voiceError,
      supported: getSpeechRecognitionCtor() !== null,
      isContinuousMode,
      beginFollowUpRecording,
      exitContinuousMode,
      resetContinuousIdleTimer,
      setIdleExitSuspended,
    }),
    [
      beginFollowUpRecording,
      exitContinuousMode,
      isContinuousMode,
      notice,
      resetContinuousIdleTimer,
      setIdleExitSuspended,
      status,
      voiceError,
    ],
  )
}
