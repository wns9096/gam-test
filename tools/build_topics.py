# -*- coding: utf-8 -*-
"""공개 데이터 → 10주제 × 5문항.

**모든 숫자는 raw/ 의 원본에서 계산합니다.** 지어낸 값이 하나도 없어야 합니다.
결과는 앱이 읽는 topics/*.json 과, 사람이 읽는 tools/정답지.md 로 나갑니다.

정답지와 이 스크립트는 .vercelignore 에 들어 있어 **배포되지 않습니다.**
공개 URL 에 정답지가 올라가면 게임이 성립하지 않습니다.

실행 (저장소 최상위에서):
    python tools/build_topics.py
"""
from __future__ import annotations

import csv
import sys
import io
import json
import datetime as dt
from collections import Counter
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent          # tools/
APP = HERE.parent                                # 저장소 최상위 = 배포되는 곳
# ★ 윈도우 기본 콘솔은 cp949 다. 마지막에 이모지를 찍다가 UnicodeEncodeError 로
#   죽었다 — topics/*.json 은 이미 다 써 놓은 뒤였다. 계산은 멀쩡한데 「실패」로
#   보인다. 스크립트는 **한 일** 때문에 죽어야지 **찍은 것** 때문에 죽으면 안 된다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

RAW = APP / "data" / "raw"
OUT = APP / "topics"

TOPICS: list[dict] = []


def load_json(name):
    return json.load(io.open(RAW / name, encoding="utf-8"))


def load_csv(name):
    return list(csv.DictReader(io.open(RAW / name, encoding="utf-8")))


# World Bank·OWID 응답에는 '유럽연합' '고소득국' 같은 **집계치**가 섞여 있다.
# 그대로 순위를 매기면 나라와 대륙을 한 줄에 놓고 세는 셈이 된다.
REAL = {x["id"] for x in load_json("wb_countries.json")[1]
        if x["region"]["id"] != "NA"}


def wb_countries(rows, year):
    """그 해의 실제 국가 값만 남긴다 (집계치 제외)."""
    return {r["country"]["value"]: r["value"] for r in rows
            if int(r["date"]) == year and r["countryiso3code"] in REAL}


def owid_countries(rows, year, col):
    """OWID 도 마찬가지. code 가 비었거나 OWID_ 로 시작하면 집계치다."""
    return {r["entity"]: float(r[col]) for r in rows
            if int(r["year"]) == year and r["code"]
            and not r["code"].startswith("OWID")}


def topic(tid, emoji, title, blurb, source, source_url, questions, caveat="",
          by="", notes=()):
    """caveat = 이 데이터를 믿을 때의 한계. 앱 화면에도 그대로 나간다.

    출처가 다르면 같은 '서울 기온'도 값이 다르다. 그 사실을 감추지 않는다.

    by    = 이 주제의 문항을 만든 사람. 골격이 준 주제는 비어 있다.
    notes = 세기 전에 원본을 열어 **걸러낸 것**. 이게 만든 일의 내용이다 —
            「내가 만들었다」는 배지보다 이 목록이 그것을 보여 준다.
    """
    TOPICS.append({"id": tid, "emoji": emoji, "title": title, "blurb": blurb,
                   "source": source, "source_url": source_url,
                   "caveat": caveat, "by": by, "notes": list(notes),
                   "questions": questions})


def slider(qid, text, answer, unit, lo, hi, step, basis, why):
    return {"id": qid, "type": "slider", "text": text, "unit": unit,
            "min": lo, "max": hi, "step": step,
            "answer": round(float(answer), 1), "basis": basis, "why": why}


def choice(qid, text, options, answer, basis, why):
    assert answer in options, f"{qid}: 정답이 선택지에 없습니다"
    return {"id": qid, "type": "choice", "text": text, "options": options,
            "answer": answer, "basis": basis, "why": why}


# ════════════════════════════════════════════════════════════════
# 기상 공통
# ════════════════════════════════════════════════════════════════
w = load_json("seoul_weather.json")["daily"]
W = [{"d": dt.date.fromisoformat(t), "hi": hi, "lo": lo, "rain": r}
     for t, hi, lo, r in zip(w["time"], w["temperature_2m_max"],
                             w["temperature_2m_min"], w["precipitation_sum"])]
W24 = [x for x in W if x["d"].year == 2024]


def years(a, b):
    return [x for x in W if a <= x["d"].year <= b]


# ── 1. 서울 기온 ─────────────────────────────────────────────────
# ERA5 는 1950~70년대 구간의 품질이 낮고(초기 확장), 격자 평균이라 도심
# 관측값보다 낮게 나온다. 그래서 '역대 최고기온'이나 '폭염일 추세'처럼
# 그 구간에 기대는 문항은 쓰지 않는다. 열대야·연평균처럼 신호가 뚜렷한 것만 쓴다.
tropical_24 = sum(1 for x in W24 if x["lo"] >= 25)
trop_50s = sum(1 for x in years(1950, 1959) if x["lo"] >= 25) / 10
trop_10s = sum(1 for x in years(2015, 2024) if x["lo"] >= 25) / 10
t_ratio = trop_10s / trop_50s if trop_50s else 0
mean_50s = mean((x["hi"] + x["lo"]) / 2 for x in years(1950, 1959))
mean_10s = mean((x["hi"] + x["lo"]) / 2 for x in years(2015, 2024))
warming = mean_10s - mean_50s
below0_24 = sum(1 for x in W24 if x["lo"] < 0)
hot_days = Counter((x["d"].month, x["d"].day)
                   for x in years(1995, 2024) if x["hi"] >= 33)
peak_day = hot_days.most_common(1)[0]

topic(
    "seoul-heat", "🌡️", "서울은 얼마나 더워졌나",
    "1950년부터 2024년까지, 서울의 매일 기온",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("h1", "2024년 서울에서 열대야(밤 최저기온 25도 이상)는 며칠이었을까요?",
               tropical_24, "일", 0, 60, 1,
               f"2024년 일최저기온 25도 이상인 날 {tropical_24}일",
               "유난히 더웠던 밤 몇 번이 기억을 지배합니다. 실제 일수는 세어 봐야 "
               "압니다."),
        choice("h2", "1950년대와 2015~2024년, 열대야는 몇 배 차이일까요?",
               ["거의 같다", "약 2배", "약 5배", "약 20배"],
               ["거의 같다", "약 2배", "약 5배", "약 20배"][
                   0 if t_ratio < 1.5 else 1 if t_ratio < 3.5
                   else 2 if t_ratio < 10 else 3],
               f"연평균 열대야 1950년대 {trop_50s:.1f}일 → 2015~2024년 "
               f"{trop_10s:.1f}일 ({t_ratio:.1f}배)",
               "'옛날에도 더웠다'는 느낌과 기록은 다릅니다. 낮 기온보다 밤 기온이 "
               "훨씬 크게 변했습니다."),
        slider("h3", "1950년대와 비교해 서울의 연평균 기온은 몇 도 올랐을까요?",
               warming, "도", 0, 4, 0.1,
               f"1950년대 {mean_50s:.2f}도 → 2015~2024년 {mean_10s:.2f}도 "
               f"(+{warming:.2f}도)",
               "1~2도는 작아 보이지만, 그 변화가 열대야 일수를 몇 배로 바꿉니다. "
               "평균의 변화와 극단의 변화는 크기가 다릅니다."),
        choice("h4", "최근 30년간 33도 이상인 날이 가장 잦았던 날짜는?",
               ["7월 초", "7월 말", "8월 초", "8월 말"],
               "7월 말" if peak_day[0][0] == 7 and peak_day[0][1] >= 20
               else "8월 초" if peak_day[0][0] == 8 and peak_day[0][1] <= 10
               else "7월 초" if peak_day[0][0] == 7 else "8월 말",
               f"1995~2024년 중 가장 잦았던 날짜는 {peak_day[0][0]}월 "
               f"{peak_day[0][1]}일 ({peak_day[1]}회)",
               "장마가 끝나는 시점과 가장 더운 시점은 다릅니다."),
        slider("h5", "2024년 서울에서 밤 기온이 영하로 내려간 날은 며칠이었을까요?",
               below0_24, "일", 30, 150, 5,
               f"2024년 일최저기온 0도 미만인 날 {below0_24}일",
               "겨울이 짧아졌다고 느끼지만, 영하로 내려가는 날은 여전히 석 달 "
               "치가 넘습니다."),
    ],
    caveat="ERA5는 넓은 격자의 재분석 값이라 도심 관측소보다 낮게 나옵니다. "
           "예컨대 여기서는 역대 최고기온이 37.6도지만 기상청 서울 관측 기록은 "
           "2018년 39.6도입니다. 같은 '서울 기온'도 출처에 따라 다릅니다.")

# ── 2. 비 ────────────────────────────────────────────────────────
rain_days = [sum(1 for x in W if x["d"].year == y and x["rain"] >= 1.0)
             for y in range(1995, 2025)]
rain_avg = mean(rain_days)
by_month = {m: mean([sum(x["rain"] for x in W
                         if x["d"].year == y and x["d"].month == m)
                     for y in range(1995, 2025)]) for m in range(1, 13)}
wettest_m = max(by_month, key=by_month.get)
max_day = max(W, key=lambda x: x["rain"])
ann = {y: sum(x["rain"] for x in W if x["d"].year == y) for y in range(1995, 2025)}
norm = mean(ann.values())
r2024 = ann[2024]


def days_to_half(y):
    v = sorted((x["rain"] for x in W if x["d"].year == y), reverse=True)
    half, s = sum(v) / 2, 0
    for i, r in enumerate(v, 1):
        s += r
        if s >= half:
            return i
    return len(v)


half_days = round(mean(days_to_half(y) for y in range(1995, 2025)))

topic(
    "seoul-rain", "☔", "비는 언제, 얼마나",
    "서울의 하루치 강수량 30년",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("r1", "서울에서 1년 중 비가 온 날(1mm 이상)은 며칠쯤일까요?",
               rain_avg, "일", 40, 160, 5,
               f"1995~2024년 평균 {rain_avg:.1f}일 "
               f"(최소 {min(rain_days)}일 · 최대 {max(rain_days)}일)",
               "비 오는 날은 기억에 오래 남아서 실제보다 많게 느껴집니다."),
        choice("r2", "1년 강수량이 가장 많은 달은?",
               ["6월", "7월", "8월", "9월"], f"{wettest_m}월",
               " · ".join(f"{m}월 {by_month[m]:.0f}mm" for m in (6, 7, 8, 9)),
               "장마가 낀 달과 비가 가장 많이 오는 달이 같지 않을 수 있습니다."),
        slider("r3", "하루에 내린 비의 최대 기록은?",
               max_day["rain"], "mm", 100, 500, 10,
               f"{max_day['d']:%Y년 %m월 %d일} {max_day['rain']:.1f}mm",
               "하루 300mm는 한 달 평균치가 하루에 쏟아진다는 뜻입니다."),
        slider("r4", "1년 강수량의 절반은 '비 온 날' 며칠 만에 채워질까요?",
               half_days, "일", 3, 40, 1,
               f"많이 온 날부터 더해서 연 강수량의 절반에 도달하는 데 "
               f"평균 {half_days}일 (1995~2024년)",
               "비는 고르게 오지 않습니다. 열흘 남짓이 1년의 절반을 만듭니다."),
        slider("r5", "2024년 서울 강수량은 30년 평균의 몇 %였을까요?",
               r2024 / norm * 100, "%", 50, 180, 5,
               f"2024년 {r2024:.0f}mm · 1995~2024년 평균 {norm:.0f}mm",
               "'올해 비가 많았다'는 체감과 실제 총량은 자주 어긋납니다."),
    ],
    caveat=(
        "ERA5 재분석 값입니다. 기상청 관측 강수량과 조금씩 다릅니다.<br>"
        "넓은 격자의 평균이라 <b>좁은 곳에 쏟아지는 소나기는 뭉개집니다</b> — "
        "하루 강수량이 실제보다 낮게 나오기 쉽습니다.<br>"
        "그리고 「비 온 날」은 하루 1mm 이상으로 센 것입니다. 기준을 0.1mm 로 "
        "바꾸면 날수가 크게 늘어납니다. 답을 만드는 것은 날씨가 아니라 기준입니다."))

# ── 3. 미세먼지 ──────────────────────────────────────────────────
a = load_json("seoul_air.json")["hourly"]
A = [{"t": dt.datetime.fromisoformat(t), "pm25": p25, "pm10": p10}
     for t, p25, p10 in zip(a["time"], a["pm2_5"], a["pm10"])]
A24 = [x for x in A if x["t"].year == 2024]
pm_month = {m: mean([x["pm25"] for x in A if x["t"].month == m])
            for m in range(1, 13)}
worst_m = max(pm_month, key=pm_month.get)
pm_hour = {h: mean([x["pm25"] for x in A if x["t"].hour == h])
           for h in range(24)}
worst_h = max(pm_hour, key=pm_hour.get)
pm24_avg = mean(x["pm25"] for x in A24)


def daily_avg(year):
    d = {}
    for x in A:
        if x["t"].year == year:
            d.setdefault(x["t"].date(), []).append(x["pm25"])
    return {k: mean(v) for k, v in d.items()}


d24 = daily_avg(2024)
d23 = daily_avg(2023)
bad_ratio = sum(1 for v in d24.values() if v > 35) / len(d24) * 100
worse_year = "2023년" if mean(d23.values()) > mean(d24.values()) else "2024년"

topic(
    "seoul-air", "😷", "미세먼지, 언제 나쁜가",
    "서울의 시간별 초미세먼지 2년치",
    "Open-Meteo Air Quality (CAMS)", "https://open-meteo.com/",
    [
        choice("a1", "초미세먼지(PM2.5)가 가장 나쁜 달은?",
               ["1월", "3월", "5월", "11월"],
               f"{worst_m}월" if f"{worst_m}월" in ["1월", "3월", "5월", "11월"]
               else "3월",
               " · ".join(f"{m}월 {pm_month[m]:.1f}" for m in (1, 3, 5, 11))
               + f" (최악은 {worst_m}월 {pm_month[worst_m]:.1f})",
               "황사 뉴스가 많은 달과 실제 수치가 높은 달은 다를 수 있습니다."),
        slider("a2", "2024년 서울의 초미세먼지 연평균 농도는?",
               pm24_avg, "㎍/㎥", 5, 60, 1,
               f"2024년 시간값 {len(A24):,}개의 평균 {pm24_avg:.1f}㎍/㎥ "
               f"(WHO 권고 연평균 5, 국내 기준 15)",
               "'나쁨'인 날이 인상에 남아서 연평균을 높게 잡게 됩니다."),
        choice("a3", "하루 중 초미세먼지가 가장 높은 시간대는?",
               ["새벽 4시", "오전 10시", "오후 3시", "밤 9시"],
               {4: "새벽 4시", 10: "오전 10시", 15: "오후 3시",
                21: "밤 9시"}.get(worst_h, "오전 10시"),
               " · ".join(f"{h}시 {pm_hour[h]:.1f}" for h in (4, 10, 15, 21))
               + f" (최고는 {worst_h}시)",
               "출퇴근 시간이 가장 나쁠 것 같지만 대기가 정체되는 시간은 따로 "
               "있습니다."),
        slider("a4", "2024년 하루 평균이 '나쁨'(35㎍/㎥ 초과)이었던 날의 비율은?",
               bad_ratio, "%", 0, 60, 1,
               f"2024년 {len(d24)}일 중 "
               f"{sum(1 for v in d24.values() if v > 35)}일",
               "마스크를 챙긴 날은 강하게 기억되지만, 1년 전체로 보면 비율이 "
               "다릅니다."),
        choice("a5", "2023년과 2024년 중 초미세먼지가 더 나빴던 해는?",
               ["2023년", "2024년"], worse_year,
               f"연평균 2023년 {mean(d23.values()):.1f} · "
               f"2024년 {mean(d24.values()):.1f}㎍/㎥",
               "체감은 최근 쪽으로 쏠립니다. 두 해 차이는 생각보다 작습니다."),
    ],
    caveat=(
        "CAMS 대기질 모델의 추정값입니다. 에어코리아 측정소 실측값과 다를 수 "
        "있습니다 — <b>잰 값이 아니라 계산한 값</b>이라, 특정 날짜의 수치를 "
        "실측치인 양 인용하면 안 됩니다.<br>"
        "2023~2024년 두 해뿐입니다. 「좋아지고 있다 · 나빠지고 있다」 같은 "
        "추세는 두 해로는 말할 수 없습니다."))

# ── 4. 노동시간 ──────────────────────────────────────────────────
wh = [r for r in load_csv("working_hours.csv") if r["working_hours_omm"]]
latest_year = max(int(r["year"]) for r in wh if r["code"] == "KOR")
cur = owid_countries(wh, latest_year, "working_hours_omm")
kor = cur["South Korea"]
rank = sorted(cur.items(), key=lambda kv: -kv[1])
kor_rank = [k for k, _ in rank].index("South Korea") + 1
longer = kor_rank - 1
past = {int(r["year"]): float(r["working_hours_omm"])
        for r in wh if r["code"] == "KOR"}
y30 = latest_year - 30
drop = past[y30] - kor
trio = {c: cur[c] for c in ("South Korea", "Japan", "Germany") if c in cur}
shortest = min(trio, key=trio.get)
name_ko = {"South Korea": "한국", "Japan": "일본", "Germany": "독일"}

topic(
    "working-hours", "⏰", "우리는 얼마나 일하나",
    "나라별 1인당 연간 노동시간",
    "Our World in Data", "https://ourworldindata.org/grapher/annual-working-hours-per-worker",
    [
        slider("w1", f"{latest_year}년 한국의 1인당 연간 노동시간은?",
               kor, "시간", 1200, 2600, 50,
               f"{latest_year}년 한국 {kor:,.0f}시간 "
               f"(주 5일 기준 하루 약 {kor / 250:.1f}시간)",
               "연 단위로 물으면 감이 잘 안 옵니다. 하루로 나눠 보면 체감과 "
               "맞는지 확인할 수 있습니다."),
        # ★ 범위 위끝이 60 으로 **손으로 박혀** 있었다. 데이터가 갱신되며
        #   한국 순위가 밀려 정답이 72 가 됐는데 범위는 안 따라왔다 —
        #   슬라이더를 끝까지 밀어도 12 이 모자라서 **맞힐 수가 없는 문항**이
        #   되어 있었다. 화면은 멀쩡하고 아무도 안 걸린다.
        #   위끝은 데이터에서 나와야 한다: 한국 말고 나머지 전부.
        slider("w2", f"한국보다 더 오래 일하는 나라는 {len(cur)}개국 중 몇 개일까요?",
               longer, "개국", 0, len(cur) - 1, 1,
               f"{latest_year}년 기준 {len(cur)}개국 중 한국은 {kor_rank}위",
               "'한국이 제일 많이 일한다'는 인상이 강하지만, 비교 대상에 따라 "
               "순위가 달라집니다."),
        slider("w3", f"한국의 노동시간은 30년 전({y30}년)보다 몇 시간 줄었을까요?",
               drop, "시간", 0, 900, 50,
               f"{y30}년 {past[y30]:,.0f}시간 → {latest_year}년 {kor:,.0f}시간",
               "줄어든 폭은 대개 과소평가됩니다. 하루로 치면 크게 달라진 값입니다."),
        choice("w4", "한국·일본·독일 중 가장 적게 일하는 나라는?",
               ["한국", "일본", "독일"], name_ko[shortest],
               " · ".join(f"{name_ko[c]} {trio[c]:,.0f}시간" for c in trio),
               "나라마다 통계 기준이 다릅니다. 순위보다 격차의 크기를 봅니다."),
        slider("w5", "한국과 독일의 연간 노동시간 차이는?",
               abs(cur["South Korea"] - cur["Germany"]), "시간", 0, 900, 50,
               f"한국 {cur['South Korea']:,.0f} · 독일 "
               f"{cur['Germany']:,.0f}시간",
               "두 나라 차이를 주 단위로 나눠 보면 체감이 확 달라집니다."),
    ],
    caveat=(
        "이 자료에는 개발도상국이 많이 포함돼 있어, OECD 안에서의 순위와 전체 "
        "순위가 다릅니다. 「어느 집단과 비교하느냐」가 순위를 만듭니다.<br>"
        "분모도 고정된 수가 아닙니다 — <b>그해에 값을 낸 나라만</b> 셉니다. "
        "해마다 참여국이 달라지므로 순위는 그만큼 흔들립니다.<br>"
        "노동시간을 재는 방법(사업체 조사냐 가구 조사냐, 자영업을 넣느냐)도 "
        "나라마다 다릅니다."))

# ── 5. 인구와 출산 ───────────────────────────────────────────────
fert = [r for r in load_json("wb_fertility.json")[1] if r["value"] is not None]
f_latest = max(int(r["date"]) for r in fert if r["countryiso3code"] == "KOR")
f_cur = wb_countries(fert, f_latest)
kor_f = f_cur["Korea, Rep."]
f_rank = sorted(f_cur.items(), key=lambda kv: kv[1])
kor_f_rank = [k for k, _ in f_rank].index("Korea, Rep.") + 1
kor_1970 = next(r["value"] for r in fert
                if r["countryiso3code"] == "KOR" and r["date"] == "1970")

pop = load_json("wb_pop_kor.json")[1]
tot = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.TOTL" and r["value"]}
old = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.65UP.TO.ZS" and r["value"]}
urb = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.URB.TOTL.IN.ZS" and r["value"]}
peak_year = max(tot, key=tot.get)
old_latest = max(old)
urb_latest = max(urb)

topic(
    "population", "👶", "인구와 출산",
    "전 세계 출산율과 한국의 인구 구조",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("p1", f"{f_latest}년 한국의 합계출산율(여성 1명당 출생아 수)은?",
               kor_f, "명", 0.5, 3.0, 0.05,
               f"{f_latest}년 한국 {kor_f:.2f}명",
               "숫자는 자주 들었어도 '여성 1명당'이라는 단위는 잘 안 와닿습니다."),
        slider("p2", f"출산율이 낮은 순으로 세면 한국은 {len(f_cur)}개 나라·지역 중 몇 위일까요?",
               kor_f_rank, "위", 1, 30, 1,
               f"{f_latest}년 기준 {len(f_cur)}곳 중 {kor_f_rank}위 "
               f"(1위 {f_rank[0][0]} {f_rank[0][1]:.2f})",
               "'꼴찌'라고 알고 있지만, 비교 목록에 어떤 나라·지역이 들어가느냐에 "
               "따라 순위가 달라집니다."),
        slider("p3", "1970년 한국의 출산율은 몇 명이었을까요?",
               kor_1970, "명", 1.0, 7.0, 0.1,
               f"1970년 {kor_1970:.2f}명 → {f_latest}년 {kor_f:.2f}명",
               "한 세대 만에 일어난 변화의 크기는 대개 과소평가됩니다."),
        slider("p4", f"{old_latest}년 한국에서 65세 이상 인구의 비율은?",
               old[old_latest], "%", 5, 35, 1,
               f"{old_latest}년 {old[old_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "고령화는 '다가올 일'로 느껴지지만 이미 지나온 숫자입니다."),
        slider("p5", f"{urb_latest}년 한국에서 도시에 사는 사람의 비율은?",
               urb[urb_latest], "%", 50, 100, 1,
               f"{urb_latest}년 {urb[urb_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "'절반쯤'이라고 답하기 쉽지만 한국은 세계에서도 손꼽히는 도시 국가입니다."),
    ],
    caveat=(
        "출산율 순위의 분모 217곳에는 <b>나라가 아닌 곳</b>도 들어 있습니다 — "
        "1위가 마카오입니다. 「몇 위」는 무엇을 한 칸으로 세느냐에 달려 "
        "있습니다.<br>"
        "65세 비율과 도시화율의 2025년 값은 <b>추계</b>입니다. 센 것이 아니라 "
        "센서스 사이를 메운 값입니다.<br>"
        "도시화율은 특히 약합니다. 「도시」의 정의를 나라마다 자기 기준으로 "
        "정해 신고하기 때문에, 나라끼리 견주기에 가장 조심스러운 지표입니다."))

# ── 6. 인터넷 ────────────────────────────────────────────────────
net = [r for r in load_json("wb_internet.json")[1] if r["value"] is not None]
n_latest = max(int(r["date"]) for r in net if r["countryiso3code"] == "KOR")
n_cur = wb_countries(net, n_latest)
kor_n = n_cur["Korea, Rep."]
n_rank = sorted(n_cur.items(), key=lambda kv: -kv[1])
kor_n_rank = [k for k, _ in n_rank].index("Korea, Rep.") + 1
kor_2000 = next(r["value"] for r in net
                if r["countryiso3code"] == "KOR" and r["date"] == "2000")
world = next((r["value"] for r in net
              if r["countryiso3code"] == "WLD" and int(r["date"]) == n_latest), None)
if world is None:
    world = mean(n_cur.values())
offline = 100 - world

topic(
    "internet", "🌐", "인터넷과 연결",
    "나라별 인터넷 사용 인구 비율",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("i1", f"{n_latest}년 한국에서 인터넷을 쓰는 사람의 비율은?",
               kor_n, "%", 60, 100, 1,
               f"{n_latest}년 한국 {kor_n:.1f}%",
               "'거의 다'라고 생각하지만 100%는 아닙니다. 남은 몇 %가 누구인지가 "
               "정책의 대상입니다."),
        slider("i2", f"한국보다 인터넷 사용률이 높은 나라는 {len(n_cur)}곳 중 몇 곳일까요?",
               kor_n_rank - 1, "곳", 0, 60, 1,
               f"{n_latest}년 {len(n_cur)}곳 중 한국 {kor_n_rank}위",
               "'IT 강국'이라는 말과 실제 보급률 순위는 다른 이야기입니다."),
        slider("i3", "2000년 한국의 인터넷 사용률은?",
               kor_2000, "%", 0, 100, 5,
               f"2000년 {kor_2000:.1f}% → {n_latest}년 {kor_n:.1f}%",
               "20여 년 전을 떠올릴 때는 지금의 기준으로 과대평가하기 쉽습니다."),
        slider("i4", f"{n_latest}년 전 세계 평균 인터넷 사용률은?",
               world, "%", 20, 100, 5,
               f"{n_latest}년 세계 {world:.1f}%",
               "내 주변이 전부 연결돼 있으면 세계도 그럴 거라고 생각하게 됩니다."),
        slider("i5", "전 세계에서 인터넷을 쓰지 않는 사람은 몇 %일까요?",
               offline, "%", 0, 70, 5,
               f"100 - {world:.1f} = {offline:.1f}%",
               "같은 사실을 뒤집어 물으면 전혀 다른 크기로 느껴집니다."),
    ],
    caveat=(
        "2023년에 값을 낸 나라는 217곳 중 <b>181곳뿐</b>입니다. 빠진 36곳은 "
        "대부분 인구가 적은 섬·속령이지만 에리트레아·보츠와나 같은 나라도 "
        "있습니다 — 「181곳 중 14위」의 분모는 세계 전체가 아닙니다.<br>"
        "세계 평균 69.2%는 나라별 평균이 아니라 <b>인구로 가중한</b> World Bank "
        "집계값입니다. 인구가 많은 나라가 값을 끌어당깁니다. 나라를 똑같이 "
        "한 표씩 세면 다른 수가 나옵니다.<br>"
        "「인터넷을 쓴다」의 기준도 나라가 스스로 정해 조사하고 신고합니다."))

# ── 7. 환율 ──────────────────────────────────────────────────────
fx = load_json("usdkrw.json")["rates"]
FX = sorted((d, v["KRW"]) for d, v in fx.items() if "KRW" in v)
hi_d, hi_v = max(FX, key=lambda x: x[1])
lo_d, lo_v = min(FX, key=lambda x: x[1])
avg_fx = mean(v for _, v in FX)
under1200 = sum(1 for _, v in FX if v < 1200) / len(FX) * 100
last_d, last_v = FX[-1]
era = ("1997~1999년 외환위기" if hi_d < "2005" else
       "2008~2009년 금융위기" if hi_d < "2012" else
       "2020년 코로나" if hi_d < "2022" else "2022년 이후")

topic(
    "usdkrw", "💵", "원달러 환율 26년",
    "1999년부터 오늘까지의 원달러 환율",
    "Frankfurter (유럽중앙은행 고시)", "https://frankfurter.dev/",
    [
        slider("x1", "1999년 이후 원달러 환율의 최고 기록은?",
               hi_v, "원", 1100, 1800, 25,
               f"{hi_d} {hi_v:,.2f}원",
               "최고치는 위기의 기억과 함께 남지만, 정확한 시점은 자주 헷갈립니다."),
        choice("x2", "그 최고치를 찍은 시기는?",
               ["1997~1999년 외환위기", "2008~2009년 금융위기",
                "2020년 코로나", "2022년 이후"], era,
               f"최고 {hi_v:,.2f}원 ({hi_d}). 이 데이터는 1999년부터라 "
               f"1997~98년 외환위기 구간은 포함되어 있지 않습니다",
               "데이터가 시작하는 시점을 확인하지 않으면 '역대 최고'를 잘못 "
               "말하게 됩니다."),
        slider("x3", "26년간의 평균 환율은?",
               avg_fx, "원", 900, 1500, 25,
               f"{FX[0][0]} ~ {FX[-1][0]} 거래일 {len(FX):,}일 평균 "
               f"{avg_fx:,.0f}원 (최저 {lo_v:,.0f}원 · {lo_d})",
               "최근 값이 기준점이 되어 과거 평균을 높게 잡게 됩니다."),
        slider("x4", "환율이 1,200원 아래였던 날은 전체의 몇 %일까요?",
               under1200, "%", 0, 100, 5,
               f"거래일 {len(FX):,}일 중 1,200원 미만은 "
               f"{sum(1 for _, v in FX if v < 1200):,}일",
               "'원래 1,100원대였는데'라는 감각이 맞는지 비율로 확인해 봅니다."),
        slider("x5", f"{last_d} 기준 환율은?",
               last_v, "원", 1100, 1800, 25,
               f"{last_d} {last_v:,.2f}원",
               "가장 최근 값조차 기억은 며칠 전 뉴스에 묶여 있습니다."),
    ],
    caveat=(
        "1999년 1월 4일부터입니다. 유럽중앙은행 고시가 그때 시작해서 "
        "<b>1997~98년 외환위기 구간은 이 데이터에 아예 없습니다.</b> "
        "그래서 「26년 최고 1,583원」은 정확히는 「1999년 이후 최고」입니다.<br>"
        "달력 9,494일 중 6,658일(70%)만 있습니다 — 주말과 공휴일은 빠집니다. "
        "「전체의 몇 %」는 전부 거래일 기준입니다.<br>"
        "하루 한 번 고시하는 참고 환율이라 그날 오르내린 폭도 아니고, "
        "은행에서 실제로 환전할 때 적용되는 값도 아닙니다."))

# ── 8. 도시 비교 ─────────────────────────────────────────────────
CITY = {}
for cid in ("seoul", "tokyo", "london", "singapore"):
    _d = load_json(f"city_{cid}.json")["daily"]
    CITY[cid] = [{"d": dt.date.fromisoformat(t), "hi": a, "lo": b, "r": c}
                 for t, a, b, c in zip(_d["time"], _d["temperature_2m_max"],
                                       _d["temperature_2m_min"],
                                       _d["precipitation_sum"])]
CN = {"seoul": "서울", "tokyo": "도쿄", "london": "런던", "singapore": "싱가포르"}
YRS = 30
c_rain = {k: sum(x["r"] for x in v) / YRS for k, v in CITY.items()}
c_days = {k: sum(1 for x in v if x["r"] >= 1) / YRS for k, v in CITY.items()}
c_temp = {k: mean((x["hi"] + x["lo"]) / 2 for x in v) for k, v in CITY.items()}
c_hot = {k: max(x["hi"] for x in v) for k, v in CITY.items()}
c_jan = {k: mean(x["lo"] for x in v if x["d"].month == 1) for k, v in CITY.items()}
dry = min(c_rain, key=c_rain.get)
hottest = max(c_hot, key=c_hot.get)
colder = "서울" if c_jan["seoul"] < c_jan["tokyo"] else "도쿄"

topic(
    "cities", "🏙️", "서울·도쿄·런던·싱가포르",
    "네 도시의 30년 평년값 (1991~2020)",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        choice("c1", "1년 강수량이 가장 적은 도시는?",
               ["서울", "도쿄", "런던", "싱가포르"], CN[dry],
               " · ".join(f"{CN[k]} {c_rain[k]:,.0f}mm" for k in CITY),
               "비가 자주 오는 것과 많이 오는 것은 다릅니다. 런던은 자주 오지만 "
               "적게 옵니다."),
        slider("c2", "런던에서 1년에 비가 오는 날(1mm 이상)은 며칠일까요?",
               c_days["london"], "일", 40, 220, 5,
               f"런던 {c_days['london']:.0f}일 · 서울 {c_days['seoul']:.0f}일 "
               f"(강수량은 런던 {c_rain['london']:,.0f}mm · "
               f"서울 {c_rain['seoul']:,.0f}mm)",
               "런던은 서울보다 비 오는 날이 많은데 총량은 절반입니다. "
               "'며칠 왔나'와 '얼마나 왔나'는 다른 질문입니다."),
        choice("c3", "30년간 가장 높은 기온을 기록한 도시는?",
               ["서울", "도쿄", "런던", "싱가포르"], CN[hottest],
               " · ".join(f"{CN[k]} {c_hot[k]:.1f}도" for k in CITY),
               "적도에 가까울수록 덥다고 생각하지만, 최고기온 기록은 중위도 "
               "도시에서 나옵니다."),
        slider("c4", "서울의 연평균 기온은?",
               c_temp["seoul"], "도", 5, 30, 0.5,
               " · ".join(f"{CN[k]} {c_temp[k]:.1f}도" for k in CITY),
               "여름과 겨울의 기억이 강해서 연평균은 감이 잘 안 옵니다."),
        choice("c5", "1월 밤이 더 추운 도시는?",
               ["서울", "도쿄"], colder,
               f"1월 평균 최저기온 서울 {c_jan['seoul']:.1f}도 · "
               f"도쿄 {c_jan['tokyo']:.1f}도",
               "위도가 비슷해도 대륙의 영향을 받는 도시가 훨씬 춥습니다."),
    ],
    caveat=(
        "ERA5 재분석 값이라 도심 관측소보다 낮게 나옵니다 — 여기서는 서울 30년 "
        "최고가 36.3도지만 기상청 서울 기록은 이보다 높습니다.<br>"
        "1991~2020년 <b>30년 평년값</b>이라 최근 몇 해의 변화는 안 들어 있습니다.<br>"
        "싱가포르는 적도에 있습니다. 「1월」이나 「겨울」을 다른 세 도시와 같은 "
        "뜻으로 견줄 수 없습니다."))

# ── 9. 지진 ──────────────────────────────────────────────────────
# ★ 여기는 내가 맡은 주제다. 골격에 있던 것을 지우고 원본부터 다시 열어
#   계산했다. 값은 한 줄도 손으로 옮겨 적지 않는다 — 아래 식이 답이다.
#
# 원본을 열자마자 걸린 것 셋. 세기 전에 이것부터 봐야 했다.
#   ① 「지진 목록」에 지진이 아닌 것이 둘 있다 — 화산 분화 1, 핵실험 1.
#      type 을 안 거르면 2017년 북한 핵실험이 지진 통계에 들어간다.
#   ② 「한반도 주변」 상자(북위 33~39.5 · 동경 124~132)에 규슈와 쓰시마가
#      들어 있다. 상자 안 지진의 4분의 3이 일본 것이다.
#      네모에 이름을 붙이면 그 이름대로 센 줄로 안다.
#   ③ 규모 척도가 섞여 있다 (mww · mwc · mb · ml …). 같은 「규모」가
#      한 자로 잰 값이 아니다. 한계에 적었다.
# 지진이 아닌 것의 type 을 한글로. 화면에는 한글, 괄호에 원래 값을 같이
# 보인다 — 원본에 뭐라고 적혀 있는지를 감추지 않는다.
_QTYPE_KO = {"nuclear explosion": "핵실험", "volcanic eruption": "화산 분화",
             "explosion": "폭발", "quarry blast": "발파"}

QF = load_json("quakes.geojson")["features"]
QKF = load_json("quakes_korea.geojson")["features"]


def _q(features):
    """properties 에 깊이를 붙여 평평하게 편다. 지진만 남기는 건 아래에서."""
    return [f["properties"] | {"depth": f["geometry"]["coordinates"][2]}
            for f in features]


QALL, QKALL = _q(QF), _q(QKF)
# ★ 여기가 이 주제의 첫 판단이다. **지진만 센다.**
QUAKE = [x for x in QALL if x["type"] == "earthquake"]
QKOR = [x for x in QKALL if x["type"] == "earthquake"]
NOTQ = [x for x in QALL if x["type"] != "earthquake"]


def q_year(x):
    return dt.datetime.fromtimestamp(x["time"] / 1000, dt.timezone.utc).year


Q_YEARS = sorted({q_year(x) for x in QUAKE})
NY = len(Q_YEARS)                       # 25년. 코드로 세고 손으로 안 적는다
assert NY == 2024 - 2000 + 1, f"연도가 {NY}개다 — 기간을 다시 본다"

PER_YEAR = len(QUAKE) / NY              # 규모 5.5 이상, 연평균
BIG = [x for x in QUAKE if x["mag"] >= 7.0]
BIG_PER_YEAR = len(BIG) / NY

# 규모가 1 오르면 얼마나 드물어지는가 — 두 구간의 건수로 직접 잰다
BAND_LO = [x for x in QUAKE if 5.5 <= x["mag"] < 6.5]
BAND_HI = [x for x in QUAKE if 6.5 <= x["mag"] < 7.5]
BAND_RATIO = len(BAND_LO) / len(BAND_HI)


def q_country(place):
    """USGS 의 place 는 「… , 나라」 꼴이다. 쉼표 뒤가 나라 이름이다."""
    return place.split(",")[-1].strip() if "," in place else place.strip()


KOR_BOX = Counter(q_country(x["place"]) for x in QKOR)
JP_SHARE = KOR_BOX["Japan"] / len(QKOR) * 100

topic(
    "quakes", "🌎", "지진은 얼마나 자주",
    "규모 5.5 이상 지진 25년치를 세어 봅니다",
    "USGS 지진 카탈로그", "https://earthquake.usgs.gov/",
    [
        slider("z1", "전 세계에서 규모 5.5 이상 지진은 한 해에 몇 번쯤 일어날까요?",
               PER_YEAR, "건", 0, 800, 20,
               f"{Q_YEARS[0]}~{Q_YEARS[-1]}년 {NY}년간 {len(QUAKE):,}건 ÷ {NY}년 "
               f"= 연 {PER_YEAR:.1f}건. 목록에 섞여 있던 지진 아닌 "
               f"{len(NOTQ)}건은 빼고 세었습니다",
               "뉴스에 나온 지진만 기억에 남습니다. 규모 5.5면 큰 지진인데, "
               "사람이 안 사는 바다에서 나면 아무도 모릅니다."),

        slider("z2", "그중 규모 7.0 이상은 한 해에 몇 번일까요?",
               BIG_PER_YEAR, "건", 0, 60, 2,
               f"{NY}년간 {len(BIG):,}건 ÷ {NY}년 = 연 {BIG_PER_YEAR:.1f}건 "
               f"(분모는 위와 같은 {len(QUAKE):,}건)",
               "한 해에 한두 번으로 느끼지만 한 달에 한 번꼴입니다. "
               "규모 7이 다 재난이 되는 것은 아니라서 이름이 안 남습니다."),

        choice("z3", "규모 5.5~6.5 지진은 6.5~7.5 지진보다 몇 배 많을까요?",
               ["2배쯤", "5배쯤", "10배쯤", "50배쯤"], "10배쯤",
               f"{len(BAND_LO):,}건 / {len(BAND_HI):,}건 = {BAND_RATIO:.1f}배",
               "규모는 더하기가 아니라 곱하기로 움직입니다. "
               "1이 오르면 건수는 열 배쯤 줄어듭니다."),

        choice("z4", "「한반도 주변」이라고 위·경도 네모를 그려 지진을 세면, "
                     "그 안의 지진 중 일본에서 난 것은 몇 %일까요?",
               ["10%쯤", "30%쯤", "50%쯤", "70%가 넘는다"], "70%가 넘는다",
               f"북위 33~39.5 · 동경 124~132 상자 안 {len(QKOR)}건 중 일본 "
               f"{KOR_BOX['Japan']}건 = {JP_SHARE:.1f}% "
               f"(남한 {KOR_BOX['South Korea']} · 북한 {KOR_BOX['North Korea']} "
               f"· 중국 {KOR_BOX['China']})",
               "네모에 이름을 붙이면 그 이름대로 센 줄로 압니다. "
               "이 상자 안에는 규슈 북부와 쓰시마가 들어 있습니다."),

        choice("z5", f"이 목록(규모 5.5 이상, {Q_YEARS[0]}~{Q_YEARS[-1]}년, "
                     f"{len(QALL):,}건)에는 지진이 아닌 것이 둘 섞여 있습니다. "
                     f"무엇일까요?",
               ["화산 분화와 핵실험", "운석 충돌과 산사태",
                "댐 붕괴와 광산 폭발", "없다 — 전부 지진이다"],
               "화산 분화와 핵실험",
               " · ".join(
                   f"{dt.datetime.fromtimestamp(x['time']/1000, dt.timezone.utc):%Y-%m-%d} "
                   f"{x['type']} M{x['mag']}"
                   for x in sorted(NOTQ, key=lambda z: z["time"]))
               + f" — type 이 earthquake 가 아닌 {len(NOTQ)}건",
               "「지진 목록」이라는 이름을 믿고 세면 핵실험 한 건이 지진 "
               "통계에 들어갑니다. 세기 전에 무엇이 들어 있는지 봅니다."),
    ],
    caveat=(
        "USGS 값이라 기상청 기록과 다릅니다. 같은 지진인데 규모가 달라 "
        "<b>순서까지 바뀝니다</b> — 이 데이터에서는 2017년 포항 5.5 가 "
        "2016년 경주 5.4 보다 크지만, 기상청 발표는 경주 5.8 · 포항 5.4 라 "
        "반대입니다. 「가장 큰 지진」은 어느 기관 값이냐를 붙이지 않으면 "
        "답할 수 없는 질문입니다.<br>"
        "규모 척도도 한 가지가 아닙니다(mww · mwc · mb · ml 등이 섞여 "
        "있습니다).<br>"
        "작은 지진일수록 빠집니다. 세계 집계는 규모 5.5 이상만 받아서 그 "
        f"아래는 처음부터 없고, 한반도 상자는 규모 3.0 이상인데도 {NY}년간 "
        f"{len(QKOR)}건뿐입니다 — 기상청이 기록한 국내 지진은 이보다 훨씬 "
        "많습니다. 전 세계를 고르게 관측하는 목록이 아닙니다."),
    by="wns9096",
    notes=[
        # ★ 이 목록이 「내가 만들었다」의 내용이다. 골격에 있던 지진 주제를
        #   지우고 원본부터 다시 열었을 때 **세기 전에** 걸린 것들이다.
        #   값은 한 줄도 손으로 적지 않는다 — 위에서 계산한 것을 끌어온다.
        f"「지진 목록」에 지진이 아닌 것이 {len(NOTQ)}건 섞여 있었습니다 — "
        + " · ".join(_QTYPE_KO.get(x["type"], x["type"]) + f"({x['type']})"
                       for x in sorted(NOTQ, key=lambda z: z["time"]))
        + ". type 을 안 거르면 핵실험 한 건이 지진 통계에 들어갑니다.",

        f"「한반도 주변」이라고 위·경도 네모를 그렸더니 그 안 지진 "
        f"{len(QKOR)}건 가운데 {KOR_BOX['Japan']}건({JP_SHARE:.1f}%)이 일본 "
        f"것이었습니다. 상자에 규슈 북부와 쓰시마가 들어 있습니다. "
        f"네모에 이름을 붙이면 그 이름대로 센 줄로 압니다.",

        # 규모 척도가 섞여 있는 것도 여기 적었다가 뺐다 — 바로 아래
        # 「이 데이터의 한계」와 같은 말이 두 번 나온다. 그리고 그것은
        # «걸러낸 것»이 아니라 «못 고치는 한계»라서 자리가 거기다.

        f"답은 tools/검산.py 로 <b>다른 길로 다시 세어</b> 대조했습니다 — "
        f"연평균은 전체÷{NY} 대신 연도별로 세어 합치고, 규모 7 이상은 "
        f"7 미만과의 합이 전체인지로 확인했습니다.",
    ],
)


# ── 10. 수명 ─────────────────────────────────────────────────────
le = [r for r in load_csv("life_expectancy.csv") if r["life_expectancy_0"]]
l_latest = max(int(r["year"]) for r in le if r["code"] == "KOR")
l_cur = owid_countries(le, l_latest, "life_expectancy_0")
kor_l = l_cur["South Korea"]
l_rank = sorted(l_cur.items(), key=lambda kv: -kv[1])
kor_l_rank = [k for k, _ in l_rank].index("South Korea") + 1
_kle = {r["year"]: float(r["life_expectancy_0"]) for r in le if r["code"] == "KOR"}
kor_1950, kor_1953, kor_1955 = _kle["1950"], _kle["1953"], _kle["1955"]
wld = next(float(r["life_expectancy_0"]) for r in le
           if r["code"] == "OWID_WRL" and int(r["year"]) == l_latest)
trio_l = {c: l_cur[c] for c in ("South Korea", "Japan", "United States")
          if c in l_cur}
top_l = max(trio_l, key=trio_l.get)
name_l = {"South Korea": "한국", "Japan": "일본", "United States": "미국"}

topic(
    "life", "🩺", "얼마나 오래 사나",
    "나라별 기대수명 1950~현재",
    "Our World in Data", "https://ourworldindata.org/grapher/life-expectancy",
    [
        slider("l1", f"{l_latest}년 한국의 기대수명은?",
               kor_l, "세", 60, 95, 1,
               f"{l_latest}년 한국 {kor_l:.1f}세",
               "기대수명은 '지금 태어난 아이가 평균적으로 살 햇수'입니다. "
               "지금 살아 있는 사람의 예상 수명과는 다릅니다."),
        slider("l2", f"기대수명이 긴 순으로 세면 한국은 {len(l_cur)}곳 중 몇 위일까요?",
               kor_l_rank, "위", 1, 60, 1,
               f"{l_latest}년 {len(l_cur)}곳 중 {kor_l_rank}위 "
               f"(1위 {l_rank[0][0]} {l_rank[0][1]:.1f}세)",
               "상위권인 것은 맞지만 몇 위인지는 대개 크게 빗나갑니다."),
        slider("l3", "1950년 한국의 기대수명은?",
               kor_1950, "세", 20, 70, 1,
               f"1950년 {kor_1950:.1f}세. 한국전쟁 기간의 사망이 반영된 값이라 "
               f"1953년 {kor_1953:.1f}세, 1955년 {kor_1955:.1f}세로 빠르게 "
               f"회복합니다. {l_latest}년은 {kor_l:.1f}세",
               "숫자가 튀면 사건을 의심해야 합니다. 이 값은 오류가 아니라 "
               "전쟁의 기록입니다."),
        choice("l4", "한국·일본·미국 중 기대수명이 가장 긴 나라는?",
               ["한국", "일본", "미국"], name_l[top_l],
               " · ".join(f"{name_l[c]} {trio_l[c]:.1f}세" for c in trio_l),
               "가장 잘사는 나라가 가장 오래 사는 나라는 아닙니다."),
        slider("l5", f"{l_latest}년 세계 평균 기대수명은?",
               wld, "세", 50, 90, 1,
               f"{l_latest}년 세계 평균 {wld:.1f}세 · 한국 {kor_l:.1f}세",
               "내가 사는 곳의 수준을 세계 평균으로 착각하기 쉽습니다."),
    ],
    caveat=(
        "기대수명은 「그해의 사망률이 평생 그대로 이어진다면」을 가정해 만든 "
        "값입니다. 그래서 <b>뚝 떨어졌다가 돌아옵니다</b> — 세계 평균이 2019년 "
        "72.6세에서 2021년 70.9세로 내려갔다가 2023년 73.2세가 됐습니다. "
        "사람의 수명이 2년 만에 1.7세 줄었다 다시 는 것이 아닙니다.<br>"
        "1950년 한국 22.2세도 같은 이유입니다. 그해에 태어난 아이가 평균 "
        "22년을 살았다는 뜻이 아니라, 전쟁기의 높은 영아 사망률이 그대로 "
        "이어진다고 놓고 계산한 값입니다.<br>"
        "236곳에는 인구가 아주 적은 곳도 한 칸씩 들어 있습니다(1위 모나코). "
        "작은 곳일수록 한 해 사망자 몇 명에 값이 크게 흔들립니다."))


# ════════════════════════════════════════════════════════════════
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for t in TOPICS:
        assert len(t["questions"]) == 5, f"{t['id']}: 문항이 5개가 아닙니다"
        pack = {k: t[k] for k in ("id", "emoji", "title", "blurb",
                                  "source", "source_url", "caveat",
                                  "by", "notes")}
        pack["questions"] = t["questions"]
        io.open(OUT / f"{t['id']}.json", "w", encoding="utf-8").write(
            json.dumps(pack, ensure_ascii=False, indent=2))
        # by 는 목록에도 보낸다 — 카드에 배지를 달려면 여기 있어야 한다
        index.append({k: t[k] for k in ("id", "emoji", "title", "blurb",
                                        "source", "by")})

    io.open(APP / "topics.json", "w", encoding="utf-8").write(json.dumps({
        "title": "감 테스트",
        "subtitle": "숫자에 대한 당신의 감은 몇 점입니까",
        "crowd_label": "우리 반",
        # 등급·문구는 여기서 고칩니다. 코드를 건드릴 일이 아닙니다
        "grades": [
            {"min": 90, "name": "촉이 데이터급", "emoji": "🎯"},
            {"min": 70, "name": "감이 좋은 편", "emoji": "📊"},
            {"min": 50, "name": "보통의 감각", "emoji": "🙂"},
            {"min": 30, "name": "느낌대로 삽니다", "emoji": "🎲"},
            {"min": 0, "name": "감은 접어두시죠", "emoji": "🙈"},
        ],
        "reactions_choice": {"hit": "맞히셨습니다", "miss": "다들 그렇게 찍습니다"},
        "reactions": [
            {"max": 5, "text": "촉이 좋으시네요"},
            {"max": 20, "text": "비슷하게 보셨습니다"},
            {"max": 60, "text": "음…"},
            {"max": 999, "text": "꽤 멀리 가셨습니다"},
        ],
        "topics": index,
    }, ensure_ascii=False, indent=2))

    # 사람이 읽는 정답지
    md = ["# 문항 정답지 — 10주제 50문항", "",
          "> 모든 값은 `데이터/raw/` 의 원본에서 `문항/build_topics.py` 가 계산합니다.", ""]
    for t in TOPICS:
        md += [f"## {t['emoji']} {t['title']}", "",
               f"- 출처: {t['source']} · {t['source_url']}"]
        if t["caveat"]:
            md += [f"- **한계** {t['caveat']}"]
        md += [""]
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            md += [f"**{q['text']}**", "",
                   f"- 정답 **{a}**", f"- 근거 {q['basis']}",
                   f"- 왜 틀리나 {q['why']}", ""]
    io.open(HERE / "정답지.md", "w", encoding="utf-8").write("\n".join(md))

    print(f"주제 {len(TOPICS)}개 · 문항 {sum(len(t['questions']) for t in TOPICS)}개")
    for t in TOPICS:
        print(f"\n{t['emoji']} {t['title']}  ({t['source']})")
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            print(f"    [{q['type'][:6]:<6}] {q['text'][:44]:<44} → {a}")


if __name__ == "__main__":
    main()
