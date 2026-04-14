"""
LG HelloDoctor 테스트 관리자
전체 테스트 실행 및 결과 리포트 생성

실행: python tests/test_manager.py
"""
import subprocess
import sys
import os
from datetime import datetime


def run_tests(test_file: str) -> dict:
    """단일 테스트 파일 실행 후 결과 반환"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        "file": test_file,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }


def parse_summary(stdout: str) -> str:
    """pytest 출력에서 요약 줄 추출"""
    for line in reversed(stdout.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            return line.strip()
    return "결과 없음"


def main():
    print("=" * 60)
    print("LG HelloDoctor 전체 테스트 실행")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_files = [
        "tests/test_backend.py",
        "tests/test_rag.py",
    ]

    results = []
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"[SKIP] {test_file} 파일 없음")
            continue

        print(f"\n▶ {test_file} 실행 중...")
        result = run_tests(test_file)
        results.append(result)

        status = "✅ 통과" if result["passed"] else "❌ 실패"
        summary = parse_summary(result["stdout"])
        print(f"   {status} — {summary}")

        if not result["passed"]:
            print("\n[실패 상세]")
            print(result["stdout"][-2000:])  # 마지막 2000자

    # 최종 요약
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"최종 결과: {passed}/{total} 통과")

    if passed == total:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️  실패한 테스트가 있습니다. 위 로그를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
