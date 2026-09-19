# -*- coding: utf-8 -*-
"""토요일 교안 STEP 8 점검표 중 **기계가 볼 수 있는 것**.

    python tools/점검.py

★ 교안의 점검표는 손으로 체크하는 목록이다. 손으로 체크하는 것은 한 번은
  되고 두 번째부터 안 된다. 기계가 볼 수 있는 것만 여기로 옮겼다.

★ 폰에서 보는 것(한 손으로 되는가 · 글자가 작지 않은가)은 여기서 안 본다.
  브라우저를 띄워야 알 수 있고, 그건 사람이 폰으로 직접 본다.

★ 처음에 이 점검을 bash 한 줄로 썼다가 틀렸다 —
      git log -p | grep -i key | head -3 && echo "키 있음"
  파이프라인의 종료 코드는 **마지막 명령**(head)의 것이라 늘 0 이다.
  그래서 키가 없어도 「키 있음」이 찍혔다. 늘 통과하는 검사는 검사가 아니다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):        # 윈도우 cp949 콘솔에서 안 죽게
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
MINE = "quakes"          # 내가 맡은 주제
결과: list[bool] = []


def ok(cond, 라벨, 상세=""):
    결과.append(bool(cond))
    print(f"  [{'지킴' if cond else '걸림'}] {라벨}" + (f"  — {상세}" if 상세 else ""))


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def main() -> int:
    print("토요일 STEP 8 — 기계가 볼 수 있는 것\n")

    print("── 안전 ──")
    # 키는 커밋을 지워도 이력에 남는다. 그래서 --all 로 전부 훑는다.
    키 = re.findall(r"AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}",
                    git("log", "-p", "--all"))
    ok(not 키, "키가 저장소 이력에 없다", f"{len(키)}건 발견" if 키 else "0건")

    tracked = git("ls-files").split()
    샌것 = [f for f in tracked if f.startswith("data/") or "정답지" in f]
    ok(not 샌것, "data/ 와 정답지가 안 올라갔다",
       f"{샌것}" if 샌것 else f"추적 파일 {len(tracked)}개")

    vi = (ROOT / ".vercelignore").read_text(encoding="utf-8")
    ok("tools/" in vi and "data/" in vi, "배포에서 tools/ · data/ 를 뺀다",
       " ".join(vi.split()))
    ok((ROOT / "index.html").exists(),
       "index.html 이 최상위에 있다", "아니면 배포는 성공인데 열면 404 다")

    print("\n── 내 문항 ──")
    d = json.loads((ROOT / "topics" / f"{MINE}.json").read_text(encoding="utf-8"))
    ok(len(d["questions"]) == 5, "문항이 다섯이다", f"{len(d['questions'])}개")
    ok(all(re.search(r"\d", q["basis"]) for q in d["questions"]),
       "basis 에 숫자(분모·건수)가 있다")
    ok(all(q["why"].strip() for q in d["questions"]), "💡 한 줄이 다 있다")

    # 정답이 범위 한가운데면 아무 생각 없이 가운데 두고 맞는다.
    슬 = [q for q in d["questions"] if q["type"] == "slider"]
    가운데 = [q for q in 슬
              if abs(q["answer"] - (q["min"] + q["max"]) / 2)
              < (q["max"] - q["min"]) * 0.08]
    ok(not 가운데, "슬라이더 정답이 범위 한가운데가 아니다",
       f"{[q['id'] for q in 가운데]}" if 가운데 else " · ".join(
           f"{q['id']} 답 {q['answer']:g} vs 가운데 {(q['min']+q['max'])/2:g}"
           for q in 슬))
    ok(len(d.get("caveat", "")) > 80, "「이 데이터의 한계」를 채웠다",
       f"{len(d.get('caveat', ''))}자")

    print("\n── 앱 ──")
    idx = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))["topics"]
    ok(len(idx) == 10, "주제가 열 개 그대로다", f"{len(idx)}개")
    ok(any(t["id"] == MINE for t in idx), f"내 주제({MINE})가 목록에 있다")
    빠진 = [t["id"] for t in idx
            if not (ROOT / "topics" / f"{t['id']}.json").exists()]
    ok(not 빠진, "목록의 주제마다 파일이 있다", f"{빠진}" if 빠진 else "10/10")

    # ★ 촌평은 없어도 앱이 돌아야 한다. 그 설계가 코드에 실제로 있는지 본다.
    cm = (ROOT / "api" / "comment.py").read_text(encoding="utf-8")
    ok('"comment": None' in cm and "os.environ.get" in cm,
       "키가 없으면 촌평만 빠지게 돼 있다", "앱을 멈추지 않는다")
    ok("file=sys.stderr" in cm, "촌평이 실패하면 까닭이 로그에 남는다",
       "조용히 꺼지면 모델 이름이 죽은 것을 알 수 없다")

    bad = len(결과) - sum(결과)
    print(f"\n{sum(결과)}/{len(결과)} 지킴")
    if bad:
        print("걸린 것이 다음에 할 일이다.")
    print("\n폰으로 직접 볼 것 — 한 손으로 되는가 · 글자가 작지 않은가 · "
          "가로로 밀리지 않는가 · 환경변수를 지워도 도는가")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
