"""Interface Adapters layer — Use Case 와 외부 세계 사이의 번역 계층.

Presenters(결과 포맷), Controllers(FastAPI 라우트는 main.py), Gateways 구현이 속한다.
domain 만 의존하고, 바깥(infra/프레임워크)은 의존하지 않는다.
"""
