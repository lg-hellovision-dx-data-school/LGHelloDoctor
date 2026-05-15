"""HyDE 셀의 print() 문자열에 들어간 실제 개행을 \\n 이스케이프로 치환."""
import json
from pathlib import Path

NB = Path(__file__).parent / "rag_evaluation.ipynb"

with NB.open("r", encoding="utf-8") as f:
    nb = json.load(f)

fixed_count = 0
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])

    # 패턴: print("<newline> 또는 print(f"<newline>
    # 이걸 print("\n 또는 print(f"\n 으로 바꿈
    new_src = src
    # 케이스 1: print("\n[ → print("\\n[
    new_src = new_src.replace('print("\n[', 'print("\\n[')
    # 케이스 2: print(f"\n[ → print(f"\\n[
    new_src = new_src.replace('print(f"\n[', 'print(f"\\n[')

    if new_src != src:
        c["source"] = new_src
        fixed_count += 1
        # 차이 확인
        before_lines = src.count("\n")
        after_lines = new_src.count("\n")
        print(f"Cell [{i}] 수정: 줄 수 {before_lines} → {after_lines}")

with NB.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\n총 {fixed_count}개 셀 수정")
