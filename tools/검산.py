# -*- coding: utf-8 -*-
"""내 주제(지진)의 답을 **다른 길로** 다시 세어 topics/quakes.json 과 견준다.

    python tools/검산.py

★ 왜 따로 만드나. build_topics.py 를 불러다 쓰면 같은 코드를 두 번 돌리는
  것이라 대조가 아니다. 금요일 교안 3-6 — 「생성한 주체와 검증하는 주체가
  같으면 검증이 아니다. 생성 코드를 보지 말고, 데이터 파일만 읽어서 새로
  한다.」 그래서 이 파일은 build_topics 를 **임포트하지 않는다.**

★ 그리고 세는 길을 일부러 다르게 잡았다.
    연평균      build 는 전체 ÷ 25. 여기서는 **연도별로 세어 합친다.**
    규모 7      build 는 조건 하나로 센다. 여기서는 **7 미만과 합이 전체**인지 본다.
    나라 비중   build 는 일본만 센다. 여기서는 **나라별 합이 전체**인지 본다.
  같은 값이 나와야 하고, 다르면 둘 중 하나가 틀린 것이다.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
결과: list[bool] = []


def ok(cond, 라벨, 상세=""):
    결과.append(bool(cond))
    print(f"  [{'맞음' if cond else '어긋남'}] {라벨}" + (f"  — {상세}" if 상세 else ""))


def 편다(name):
    d = json.load(io.open(RAW / name, encoding="utf-8"))["features"]
    return [f["properties"] | {"depth": f["geometry"]["coordinates"][2]} for f in d]


def 해(x):
    return dt.datetime.fromtimestamp(x["time"] / 1000, dt.timezone.utc).year


def main() -> int:
    if not (RAW / "quakes.geojson").exists():
        print("data/raw 가 없다. python tools/fetch_all.py 를 먼저 돌린다.")
        return 1
    주제 = json.loads(
        (ROOT / "topics" / "quakes.json").read_text(encoding="utf-8"))
    답 = {q["id"]: q for q in 주제["questions"]}


    전부, 상자 = 편다("quakes.geojson"), 편다("quakes_korea.geojson")
    지진 = [x for x in 전부 if x["type"] == "earthquake"]
    아님 = [x for x in 전부 if x["type"] != "earthquake"]

    print("다른 길로 다시 센다\n")
    print("── 길이 맞물리는가 ──")
    년 = Counter(해(x) for x in 지진)
    ok(sum(년.values()) == len(전부) - len(아님),
       "연도별 합 = 전체 − 지진 아닌 것",
       f"{sum(년.values()):,} = {len(전부):,} − {len(아님)}")
    ok(sorted(년) == list(range(2000, 2025)),
       "연도가 25개 빠짐없이 있다", f"{min(년)}~{max(년)} · {len(년)}개")

    print()
    print("── z1 몇 시간에 한 번 ──")
    # build 는 날수를 한 번 빼서 구한다(2025-01-01 − 2000-01-01).
    # 여기서는 **해마다 며칠인지 세어 더한다.** 윤년을 제대로 세는지가
    # 여기서 갈린다 — 25×365 로 어림하면 7일이 모자라 답이 달라진다.
    일수 = sum((dt.date(y + 1, 1, 1) - dt.date(y, 1, 1)).days for y in sorted(년))
    ok(일수 == 25 * 365 + 7, "해마다 날수를 세어 더하면 윤년 7일이 들어 있다",
       f"{일수:,}일")
    내값 = 일수 * 24 / sum(년.values())
    ok(round(내값, 1) == 답["z1"]["answer"],
       "다른 길로 구한 간격이 문항의 답과 같다",
       f"내 {내값:.2f}시간 · 문항 {답['z1']['answer']}시간")
    # ★ 여기가 재미있는 자리다. 지진 아닌 2건을 안 걸러도 소수 첫째 자리에서는
    #   같은 수가 나온다. 답은 안 움직이지만 근거 문장은 달라진다 —
    #   그래서 거르는 것은 «수를 맞추려고»가 아니라 «말을 맞추려고»다.
    안거른값 = 일수 * 24 / len(전부)
    print(f"     · 참고: 안 거르면 {안거른값:.2f} → 반올림하면 "
          f"{round(안거른값, 1)} 로 **같다**. 답은 안 움직이고 근거만 달라진다")

    print()
    print("── z2 70km 보다 깊은 것 ──")
    # build 는 깊은 쪽을 센다. 여기서는 **얕은 쪽을 세고** 합이 전체인지 본다.
    얕 = [x for x in 지진 if x["depth"] < 70]
    깊 = [x for x in 지진 if x["depth"] >= 70]
    ok(len(얕) + len(깊) == len(지진), "얕은 것 + 깊은 것 = 전체",
       f"{len(얕):,} + {len(깊):,} = {len(지진):,}")
    내값 = 100 - len(얕) / len(지진) * 100
    ok(round(내값, 1) == 답["z2"]["answer"],
       "얕은 쪽에서 빼도 문항의 답과 같다",
       f"내 {내값:.1f}% · 문항 {답['z2']['answer']}%")
    # 한계에 «28.3%가 정확히 10.0km» 라고 적었다. 그 수가 지금 파일과
    # 맞는지 본다. 적어 놓은 수는 데이터가 바뀌면 혼자 옛말이 된다.
    고정10 = sum(1 for x in 지진 if x["depth"] == 10.0) / len(지진) * 100
    ok(f"{고정10:.1f}%" in 주제.get("caveat", ""),
       "한계에 적은 «정확히 10.0km» 비율이 지금 값과 같다",
       f"{고정10:.1f}%")

    print("\n── z3 규모 한 칸의 배수 ──")
    lo = sum(1 for x in 지진 if 5.5 <= x["mag"] < 6.5)
    hi = sum(1 for x in 지진 if 6.5 <= x["mag"] < 7.5)
    배 = lo / hi
    ok(5 <= 배 <= 20 and 답["z3"]["answer"] == "10배쯤",
       "10배쯤이 맞는 보기다", f"{lo:,}/{hi:,} = {배:.1f}배")
    ok(f"{배:.1f}" in 답["z3"]["basis"], "근거에 적힌 배수가 지금 값과 같다",
       답["z3"]["basis"])

    print("\n── z4 상자 안 일본 비중 ──")
    나라 = Counter(x["place"].split(",")[-1].strip()
                   for x in 상자 if x["type"] == "earthquake")
    ok(sum(나라.values()) == len([x for x in 상자 if x["type"] == "earthquake"]),
       "나라별 합 = 상자 안 전체", f"{sum(나라.values())}건 · {dict(나라)}")
    비중 = 나라["Japan"] / sum(나라.values()) * 100
    ok(비중 > 70 and 답["z4"]["answer"] == "70%가 넘는다",
       "70%가 넘는다가 맞는 보기다", f"{나라['Japan']}/{sum(나라.values())} = {비중:.1f}%")

    print("\n── z5 지진이 아닌 것 ──")
    종류 = sorted(x["type"] for x in 아님)
    ok(종류 == ["nuclear explosion", "volcanic eruption"],
       "화산 분화 1 · 핵실험 1 이 맞다", " · ".join(종류))
    ok(답["z5"]["answer"] == "화산 분화와 핵실험", "문항의 답이 그것을 가리킨다")
    # 문항 글에 «12,336건» 이라고 적혀 있다. 데이터를 다시 받으면 늘어난다 —
    # 그때 글만 옛 수를 말하게 된다. 그래서 글에 적힌 수를 지금 파일과 견준다.
    ok(f"{len(전부):,}건" in 답["z5"]["text"],
       "문항 글이 말한 전체 건수가 지금 파일과 같다", f"{len(전부):,}건")

    bad = len(결과) - sum(결과)
    print(f"\n{sum(결과)}/{len(결과)} 맞음")
    if bad:
        print("어긋난 것이 있다. 데이터를 다시 받았으면 "
              "python tools/build_topics.py 를 돌려 문항을 다시 낸다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
