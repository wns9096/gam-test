# -*- coding: utf-8 -*-
"""**열 주제 전부**의 문항이 말이 되는지 본다.

    python tools/문항검사.py
    python tools/문항검사.py --재생성      (data/raw 에서 다시 만들어 견준다)

★ 왜 필요했나. 나는 지진 하나만 맡아 원본부터 다시 계산했고, 나머지
  아홉은 골격이 준 것을 그대로 쓰고 있었다. 「내 것만 확인했다」는
  「앱을 확인했다」가 아니다. 남이 여는 것은 열 개 전부다.
  실제로 돌리자마자 **맞힐 수 없는 문항**이 하나 나왔다(w2).

★ 차단과 경고를 가르는 기준은 하나다 —
  **그 규칙이 깨진 채로 두면 값이 틀리는가.**
  틀리면 차단, 값은 맞는데 문항이 쉬워지기만 하면 경고.
  섞어 두면 경고가 늘어나는 순간 사람이 검사를 통째로 끈다.

★ 무엇을 볼 수 있고 무엇을 못 보나.
  볼 수 있다  답이 범위 안에 있는가 · 보기 안에 정답이 있는가 ·
              근거에 수가 있는가 · 목록과 파일이 맞는가
  못 본다     그 수가 **참인가**. 그건 원본을 다시 세야 알고,
              지진은 tools/검산.py 가 한다. 나머지 아홉은 --재생성 으로
              「데이터에서 나온 것」까지만 확인한다 — 계산이 옳은지는
              아니다. 여기서 멈추는 자리를 적어 둔다.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
결과: list[bool] = []


def ok(cond, 라벨, 상세=""):
    결과.append(bool(cond))
    print(f"  [{'지킴' if cond else '걸림'}] {라벨}" + (f"  — {상세}" if 상세 else ""))


def 해시들():
    out = {}
    for f in sorted(ROOT.glob("topics/*.json")) + [ROOT / "topics.json"]:
        out[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def 재생성():
    print("── 데이터에서 다시 만들어 견준다 ──")
    if not (ROOT / "data" / "raw" / "quakes.geojson").exists():
        print("  [넘김] data/raw 가 없다. tools/fetch_all.py 를 먼저 돌린다")
        return
    전 = 해시들()
    r = subprocess.run([sys.executable, "tools/build_topics.py"], cwd=ROOT,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    ok(r.returncode == 0, "다시 만들기가 끝까지 돈다", f"종료 {r.returncode}")
    후 = 해시들()
    다름 = [k for k in 전 if 전[k] != 후.get(k)]
    ok(not 다름, "열 주제가 바이트까지 같게 다시 만들어진다",
       f"{다름}" if 다름 else f"{len(전)}개 파일 전부 같음")
    # ★ 이것이 말해 주는 것은 «파일이 데이터에서 나왔다» 까지다.
    #   계산식이 옳은지는 말해 주지 않는다. 같은 식을 두 번 돌린 것이니까.
    print()


def main() -> int:
    if "--재생성" in sys.argv:
        재생성()

    목록 = json.loads((ROOT / "topics.json").read_text(encoding="utf-8"))["topics"]
    print(f"── 목록과 파일이 맞는가 ({len(목록)}개) ──")
    ok(len(목록) == len({t["id"] for t in 목록}), "주제 id 가 겹치지 않는다")
    어긋남 = []
    for t in 목록:
        f = ROOT / "topics" / f"{t['id']}.json"
        if not f.exists():
            어긋남.append(f"{t['id']}: 파일 없음")
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for k in ("id", "emoji", "title"):
            if d.get(k) != t.get(k):
                어긋남.append(f"{t['id']}.{k}: 목록 {t.get(k)!r} ≠ 파일 {d.get(k)!r}")
    ok(not 어긋남, "목록의 id·이모지·제목이 파일과 같다",
       " / ".join(어긋남) if 어긋남 else f"{len(목록)}/{len(목록)}")
    남은 = {f.stem for f in (ROOT / "topics").glob("*.json")} - {t["id"] for t in 목록}
    ok(not 남은, "목록에 없는 주제 파일이 안 굴러다닌다",
       f"{sorted(남은)}" if 남은 else "없음")

    print()
    print("── 주제마다 · 차단만 [걸림]으로 센다 ──")
    경고들: list[str] = []
    for t in 목록:
        d = json.loads((ROOT / "topics" / f"{t['id']}.json").read_text(encoding="utf-8"))
        qs = d["questions"]
        막음, 경고 = [], []

        if len(qs) != 5:
            막음.append(f"문항 {len(qs)}개")
        if len(qs) != len({q["id"] for q in qs}):
            막음.append("문항 id 겹침")
        if not re.match(r"https?://", d.get("source_url", "")):
            막음.append("출처 주소 이상")
        if not d.get("source", "").strip():
            막음.append("출처 이름 없음")
        # 한계가 비어도 점수는 맞게 나온다. 다만 읽는 사람이 속는다.
        if len(d.get("caveat", "")) < 80:
            경고.append(f"한계 {len(d.get('caveat', ''))}자")

        for q in qs:
            자 = q["id"]
            if not re.search("[0-9]", q.get("basis", "")):
                막음.append(f"{자} 근거에 수 없음")
            if not q.get("why", "").strip():
                막음.append(f"{자} 한 줄 설명 없음")
            if not q.get("text", "").strip().endswith("?"):
                경고.append(f"{자} 물음표 없음")

            if q["type"] == "slider":
                a, lo, hi, st = q["answer"], q["min"], q["max"], q["step"]
                # ★ 이것만 차단이다. 끝까지 밀어도 정답에 못 닿으면
                #   **맞힐 수 없는 문항**이다. 실제로 w2 가 그랬다 —
                #   답이 72 인데 위끝이 60 으로 손에 박혀 있었다.
                if not (lo < a < hi):
                    막음.append(f"{자} 답 {a:g} 가 범위 {lo:g}~{hi:g} 밖 — 맞힐 수 없다")
                if st <= 0 or (hi - lo) / st < 5:
                    막음.append(f"{자} 눈금 {st} 로는 칸이 너무 적다")
                if not str(q.get("unit", "")).strip():
                    막음.append(f"{자} 단위 없음")
                # 슬라이더는 한가운데에서 시작한다(app.js). 안 만지면 답으로
                # 안 치게 막았으니 «가만히 있어도 맞는» 일은 이제 없다.
                # 그래도 한가운데면 조금만 밀어도 맞는다 — 그래서 경고다.
                if abs(a - (lo + hi) / 2) < (hi - lo) * 0.08:
                    경고.append(f"{자} 답이 시작 위치 근처({(lo + hi) / 2:g})")
                elif min(a - lo, hi - a) < (hi - lo) * 0.03:
                    경고.append(f"{자} 답이 끝에 붙음")

            elif q["type"] == "choice":
                op = q["options"]
                if q["answer"] not in op:
                    막음.append(f"{자} 정답이 보기에 없음")
                if len(op) != len(set(op)):
                    막음.append(f"{자} 보기 겹침")
                if len(op) < 3:
                    경고.append(f"{자} 보기 {len(op)}개 — 찍으면 절반")
            else:
                막음.append(f"{자} 모르는 종류 {q['type']}")

        ok(not 막음, f"{d['emoji']} {d['title']}",
           " / ".join(막음) if 막음
           else f"{len(qs)}문항" + (f" · 경고 {len(경고)}" if 경고 else ""))
        경고들 += [f"{d['title']}: {w}" for w in 경고]

    if 경고들:
        print()
        print(f"── 경고 {len(경고들)}건 · 값은 안 틀린다. 문항이 쉬워질 뿐 ──")
        for w in 경고들:
            print(f"  · {w}")

    bad = len(결과) - sum(결과)
    print()
    print(f"차단 {bad}건 · 경고 {len(경고들)}건  ({sum(결과)}/{len(결과)} 지킴)")
    print()
    print("여기서 멈추는 자리 — 이 검사는 «그 수가 참인가»를 못 본다. "
          "지진만 tools/검산.py 로 다른 길로 다시 세어 봤다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
