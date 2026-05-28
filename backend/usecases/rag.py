"""Use Case — Hybrid RAG 검색 전략 (순수 로직, 모델 의존 0).

벡터/BM25 검색과 Cross-Encoder 리랭킹의 **모델 호출**은 infra(main 합성 루트)에서 수행하고,
이 모듈은 그 결과를 결합·선별하는 **검색 전략**만 담당한다.
  - rrf_fuse: Reciprocal Rank Fusion (여러 리트리버 결과 융합)
  - select_confident: 리랭크 점수 임계 기반 상위 선택
rag_evaluation 노트북 ablation 으로 recall@3 0.74→0.85, MRR 0.72→0.86 검증된 전략.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence


def rrf_fuse(hit_lists: Sequence[List[Dict]], k: int = 60, top_n: int = 20) -> List[Dict]:
    """Reciprocal Rank Fusion — doc_id 기준으로 여러 검색 결과를 융합해 상위 top_n 반환."""
    sc: Dict[str, float] = defaultdict(float)
    info: Dict[str, Dict] = {}
    for hits in hit_lists:
        for rank, r in enumerate(hits, 1):
            sc[r["doc_id"]] += 1.0 / (k + rank)
            info[r["doc_id"]] = r
    return [info[d] for d in sorted(sc, key=lambda x: -sc[x])[:top_n]]


def select_confident(reranked: List[Dict], threshold: float = 0.0, top: int = 3) -> List[Dict]:
    """rerank_score 상위 `top` 중 임계값 이상만 채택 (저신뢰 컨텍스트 차단)."""
    top_items = sorted(reranked, key=lambda x: -x["rerank_score"])[:top]
    return [c for c in top_items if c["rerank_score"] >= threshold]
