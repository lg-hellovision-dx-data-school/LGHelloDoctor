import { useCallback, useMemo, useRef, useState } from 'react'

/** Web Speech API (Chrome/Edge — lib.dom에 타입이 없을 수 있어 최소 형태로 정의) */
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

export function supportsSpeechRecognition(): boolean {
  return getSpeechRecognitionCtor() !== null
}

function mapSpeechError(code: string): string | null {
  switch (code) {
    case 'aborted':
      return null
    case 'not-allowed':
      return '마이크 사용이 거부되었습니다. 브라우저 주소창의 자물쇠 아이콘에서 마이크를 허용해 주세요.'
    case 'no-speech':
      return '말씀을 인식하지 못했습니다. 다시 누르고 천천히 말씀해 주세요.'
    case 'audio-capture':
      return '마이크를 찾을 수 없습니다. 장치가 연결되어 있는지 확인해 주세요.'
    case 'network':
      return '음성 인식 서비스에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.'
    case 'service-not-allowed':
      return '음성 인식을 사용할 수 없습니다. Chrome 또는 Edge 최신 버전을 이용해 주세요.'
    default:
      return `음성 인식 오류: ${code}`
  }
}

export function useVoiceInput(
  onTranscript: (text: string) => void,
  options?: { onError?: (message: string) => void },
) {
  const [listening, setListening] = useState(false)
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const bufferRef = useRef('')
  const interimRef = useRef('')
  const onTranscriptRef = useRef(onTranscript)
  const onErrorRef = useRef(options?.onError)
  onTranscriptRef.current = onTranscript
  onErrorRef.current = options?.onError

  const clearVoiceError = useCallback(() => {
    setVoiceError(null)
  }, [])

  const stop = useCallback(() => {
    const rec = recognitionRef.current
    if (rec) {
      try {
        rec.stop()
      } catch {
        /* noop */
      }
    }
    recognitionRef.current = null
    setListening(false)
  }, [])

  const start = useCallback(() => {
    clearVoiceError()

    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) {
      const msg =
        '이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 또는 Microsoft Edge에서 시도해 주세요.'
      setVoiceError(msg)
      onErrorRef.current?.(msg)
      return
    }

    try {
      const rec = new Ctor()
      recognitionRef.current = rec
      bufferRef.current = ''
      interimRef.current = ''

      rec.lang = 'ko-KR'
      rec.continuous = true
      rec.interimResults = true
      rec.maxAlternatives = 1

      rec.onresult = (event: SpeechRecognitionEventLike) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          const piece = result[0]?.transcript ?? ''
          if (result.isFinal) {
            bufferRef.current += piece
            interimRef.current = ''
          } else {
            interimRef.current = piece
          }
        }
      }

      rec.onerror = (event: SpeechRecognitionErrorEventLike) => {
        const msg = mapSpeechError(event.error)
        if (msg) {
          setVoiceError(msg)
          onErrorRef.current?.(msg)
        }
        setListening(false)
        recognitionRef.current = null
        bufferRef.current = ''
        interimRef.current = ''
      }

      rec.onend = () => {
        setListening(false)
        recognitionRef.current = null
        const text = (bufferRef.current + interimRef.current).trim()
        bufferRef.current = ''
        interimRef.current = ''
        if (text) {
          onTranscriptRef.current(text)
        }
      }

      rec.start()
      setListening(true)
    } catch {
      const msg = '음성 인식을 시작할 수 없습니다. 잠시 후 다시 시도해 주세요.'
      setVoiceError(msg)
      onErrorRef.current?.(msg)
      setListening(false)
      recognitionRef.current = null
    }
  }, [clearVoiceError])

  return useMemo(
    () => ({
      listening,
      start,
      stop,
      voiceError,
      clearVoiceError,
      speechSupported: supportsSpeechRecognition(),
    }),
    [listening, start, stop, voiceError, clearVoiceError],
  )
}
