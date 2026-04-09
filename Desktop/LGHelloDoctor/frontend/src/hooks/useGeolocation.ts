import { useEffect, useState } from 'react'

/** 강남 일대 기본값 (백엔드 샘플과 동일) */
export const DEFAULT_LAT = 37.5012
export const DEFAULT_LNG = 127.0396

type GeoState = {
  lat: number
  lng: number
  /** GPS를 쓰면 true, 권한 거부·미지원·오류 시 false */
  fromDevice: boolean
}

function readCoords(position: GeolocationPosition): { lat: number; lng: number } {
  return {
    lat: position.coords.latitude,
    lng: position.coords.longitude,
  }
}

export function useGeolocation(): GeoState {
  const [state, setState] = useState<GeoState>({
    lat: DEFAULT_LAT,
    lng: DEFAULT_LNG,
    fromDevice: false,
  })

  useEffect(() => {
    if (!navigator.geolocation) {
      return
    }

    let cancelled = false
    let watchId: number | null = null

    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (cancelled) return
        const { lat, lng } = readCoords(position)
        setState({ lat, lng, fromDevice: true })
      },
      () => {
        /* 거부·타임아웃 등 — 기본 좌표 유지 */
      },
      {
        enableHighAccuracy: false,
        maximumAge: 300_000,
        timeout: 8_000,
      },
    )

    watchId = navigator.geolocation.watchPosition(
      (position) => {
        if (cancelled) return
        const { lat, lng } = readCoords(position)
        setState((prev) => {
          if (prev.lat === lat && prev.lng === lng && prev.fromDevice) return prev
          return { lat, lng, fromDevice: true }
        })
      },
      () => {
        /* 실시간 감시 실패 시 마지막 좌표 유지 */
      },
      {
        enableHighAccuracy: true,
        maximumAge: 15_000,
        timeout: 10_000,
      },
    )

    return () => {
      cancelled = true
      if (watchId != null) {
        navigator.geolocation.clearWatch(watchId)
      }
    }
  }, [])

  return state
}
