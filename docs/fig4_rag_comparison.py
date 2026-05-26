"""Figure 4: RAG 방식별 Top-3 정확도 비교 막대그래프 (논문용).

JICS_paper_v2.md §Ⅳ.4.2 (나) 표 2 시각화.
- V4 (Hybrid) 강조 (검정 채움), 나머지는 회색 채움
- 학술 스타일 (흑백 친화·Times New Roman·minimal grid)
- 출력: docs/fig4_rag_comparison.png (300 DPI)
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl

OUT = Path(__file__).parent / "fig4_rag_comparison.png"

# 데이터 (JICS_paper_v2.md 표 2)
versions = ["V1", "V2", "V3", "V4", "V5", "V6"]
methods = [
    "Keyword\n(BM25)",
    "Vector\n(ChromaDB)",
    "Query\nRewriting",
    "Hybrid\n(V+K)",
    "Hybrid\n+Rerank",
    "GraphRAG\n(Neo4j)",
]
accuracy = [42.3, 55.0, 57.4, 62.1, 57.4, 55.0]

# 학술 스타일 설정
mpl.rcParams["font.family"] = "Times New Roman"
mpl.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=300)

# 최고 성능(V4)만 진한 회색, 나머지는 옅은 회색 (전체 톤 다운)
colors = ["#D0D0D0"] * len(versions)
best_idx = accuracy.index(max(accuracy))
colors[best_idx] = "#5A5A5A"

bars = ax.bar(
    versions, accuracy,
    color=colors,
    edgecolor="#333333",
    linewidth=1.0,
    width=0.6,
)

# 막대 위에 정확도 값 표시
for bar, acc in zip(bars, accuracy):
    h = bar.get_height()
    weight = "bold" if acc == max(accuracy) else "normal"
    ax.text(
        bar.get_x() + bar.get_width() / 2, h + 0.8,
        f"{acc:.1f}%",
        ha="center", va="bottom",
        fontsize=20, fontweight=weight,
    )

# X축 라벨 (버전 + 방식)
ax.set_xticks(range(len(versions)))
ax.set_xticklabels([f"{v}\n{m}" for v, m in zip(versions, methods)], fontsize=12)

# Y축
ax.set_ylabel("Top-3 Retrieval Accuracy (%)", fontsize=20)
ax.set_ylim(0, 75)
ax.set_yticks(range(0, 76, 10))
ax.tick_params(axis="y", labelsize=12)

# 축 스타일 (학술 minimal)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_linewidth(1.0)
ax.spines["bottom"].set_linewidth(1.0)

# 가벼운 가로 그리드
ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#CCCCCC", alpha=0.7)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved: {OUT} ({OUT.stat().st_size} bytes)")
