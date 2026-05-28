"""Domain layer — Clean Architecture 최안쪽(Entities + 도메인 규칙).

외부 프레임워크(FastAPI / ChromaDB / Ollama / rdflib)를 전혀 import 하지 않는다.
의존성 규칙: 이 패키지는 어떤 바깥 계층(adapters/infra/main)도 참조하지 않는다.
"""
