"""
LG HelloDoctor — 통합 검증 관리자
전체 시스템의 배포 전 체크리스트를 실행하고 결과를 리포트로 저장합니다.

실행: python src/todo/manager.py
"""
import subprocess
import sys
import os
import json
import requests
from datetime import datetime


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
REPORT_PATH = "docs/test-report.md"


def check(name: str, fn) -> dict:
    """단일 검증 항목 실행"""
    try:
        result = fn()
        status = "✅" if result else "❌"
        return {"name": name, "passed": bool(result), "status": status, "detail": ""}
    except Exception as e:
        return {"name": name, "passed": False, "status": "❌", "detail": str(e)}


# ====== 검증 항목 ======

def check_backend_health():
    """백엔드 서버 응답 확인"""
    res = requests.get(f"{BASE_URL}/", timeout=5)
    return res.status_code == 200


def check_chat_api():
    """채팅 API 기본 응답 확인"""
    res = requests.post(f"{BASE_URL}/chat", json={
        "text": "안녕하세요",
        "session_id": "healthcheck",
        "lat": 37.5012,
        "lng": 127.0396,
    }, timeout=30)
    data = res.json()
    return (
        res.status_code == 200
        and "answer" in data
        and "intent" in data
        and "ready_for_c" in data
    )


def check_emergency_detection():
    """응급 감지 정확도 확인"""
    res = requests.post(f"{BASE_URL}/chat", json={
        "text": "숨이 안 쉬어요",
        "session_id": "emergency-check",
        "lat": 37.5012,
        "lng": 127.0396,
    }, timeout=30)
    data = res.json()
    return data.get("intent") == "emergency"


def check_korean_only_response():
    """영어 단어 혼입 없는지 확인"""
    import re
    res = requests.post(f"{BASE_URL}/chat", json={
        "text": "무릎이 아파요",
        "session_id": "korean-check",
        "lat": 37.5012,
        "lng": 127.0396,
    }, timeout=30)
    answer = res.json().get("answer", "")
    english_words = re.findall(r'\b[a-zA-Z]{2,}\b', answer)
    return len(english_words) == 0


def check_chromadb():
    """ChromaDB 문서 수 확인 (100개 이상)"""
    import chromadb
    db_path = os.environ.get("DB_PATH", "RAG/db")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_collection("medical_knowledge")
    return col.count() >= 100


def check_frontend():
    """프론트엔드 서버 응답 확인"""
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:80")
    res = requests.get(frontend_url, timeout=5)
    return res.status_code == 200


def check_env_vars():
    """필수 환경 변수 설정 확인"""
    required = ["KAKAO_API_KEY", "GROQ_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    return len(missing) == 0


# ====== 리포트 생성 ======

def generate_report(results: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    lines = [
        f"# LG HelloDoctor 통합 검증 리포트",
        f"",
        f"**실행 시각**: {now}",
        f"**결과**: {passed}/{total} 통과",
        f"",
        f"## 검증 항목",
        f"",
        f"| 항목 | 결과 | 비고 |",
        f"|------|------|------|",
    ]
    for r in results:
        detail = r["detail"][:50] if r["detail"] else "-"
        lines.append(f"| {r['name']} | {r['status']} | {detail} |")

    lines += ["", "## 판정", ""]
    if passed == total:
        lines.append("🎉 **모든 검증 통과 — 배포 준비 완료**")
    else:
        lines.append("⚠️ **일부 검증 실패 — 배포 전 수정 필요**")
        failed = [r for r in results if not r["passed"]]
        for r in failed:
            lines.append(f"- ❌ {r['name']}: {r['detail']}")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("LG HelloDoctor 통합 검증 시작")
    print(f"대상 서버: {BASE_URL}")
    print("=" * 60)

    checks = [
        ("환경 변수 설정",       check_env_vars),
        ("ChromaDB 문서 수",     check_chromadb),
        ("백엔드 서버 응답",     check_backend_health),
        ("채팅 API 응답 형식",   check_chat_api),
        ("응급 감지 정확도",     check_emergency_detection),
        ("한국어 전용 응답",     check_korean_only_response),
        ("프론트엔드 서버 응답", check_frontend),
    ]

    results = []
    for name, fn in checks:
        print(f"  검증 중: {name}...", end=" ", flush=True)
        result = check(name, fn)
        results.append(result)
        print(result["status"])

    # 리포트 저장
    os.makedirs("docs", exist_ok=True)
    report = generate_report(results)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n리포트 저장: {REPORT_PATH}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n최종: {passed}/{total} 통과")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
