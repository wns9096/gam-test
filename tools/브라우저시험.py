# -*- coding: utf-8 -*-
"""진짜 브라우저로 연다. 내가 만든 길이 아니라 **남이 가는 길**로 간다.

    python tools/브라우저시험.py
    python tools/브라우저시험.py --보이게      (창을 띄워 눈으로 본다)

  pip install playwright && playwright install chromium

★ 서버를 스스로 띄운다. 예전에 이미 떠 있던 8765 포트에 붙였다가
  **다른 폴더**를 보고 있는 서버였다 — app.js 가 404 인데 화면은 떠서,
  8초를 기다리다 엉뚱한 곳에서 실패했다. 붙이지 말고 내가 띄운다.

★ 폰 너비(390)로 본다. 이 앱은 폰에서 보는 물건이다.
"""
from __future__ import annotations

import contextlib
import functools
import http.server
import socket
import socketserver
import sys
import threading
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


@contextlib.contextmanager
def 서버():
    with socket.socket() as s:                 # 안 쓰는 포트를 받아 온다
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    class 조용히(http.server.SimpleHTTPRequestHandler):
        # ★ log_message 는 **핸들러**의 것이다. 서버 객체에 걸었더니
        #   접속 기록이 그대로 찍혀 검사 결과를 덮어 버렸다.
        def log_message(self, *a):
            pass

    h = functools.partial(조용히, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", port), h)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        srv.shutdown()
        srv.server_close()


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 가 없다. pip install playwright "
              "&& playwright install chromium")
        return 1

    보이게 = "--보이게" in sys.argv
    with 서버() as B, sync_playwright() as pw:
        print(f"연다 — {B}\n")
        b = pw.chromium.launch(headless=not 보이게)
        pg = b.new_page(viewport={"width": 390, "height": 844})
        오류: list[str] = []
        pg.on("console",
              lambda m: 오류.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: 오류.append(f"pageerror {e}"))

        print("── 안 만진 슬라이더는 답이 아니다 ──")
        # ★ 여기에 구멍이 있었다. 슬라이더가 한가운데에서 시작하는데 바로
        #   넘어갈 수 있었다. 손도 안 대고 제출하면 환율 x5 는 100점,
        #   환율 주제는 평균 65점이 나왔다(객관식을 전부 0점으로 쳐도).
        pg.goto(f"{B}/?t=usdkrw", wait_until="networkidle")
        pg.wait_for_selector("#view-quiz:not([hidden])", timeout=10000)
        ok(pg.inner_text("#q-count").startswith("1"), "주소로 바로 열린다",
           pg.inner_text("#q-count"))
        ok(pg.is_disabled("#btn-next"), "손도 안 댔으면 «다음»이 막혀 있다")
        pg.click("#btn-next", force=True)
        ok(pg.inner_text("#q-count").startswith("1"),
           "막힌 버튼을 눌러도 안 넘어간다", pg.inner_text("#q-count"))
        pg.locator("#slider").focus()
        pg.keyboard.press("ArrowRight")
        ok(not pg.is_disabled("#btn-next"), "한 번 움직이면 «다음»이 열린다")

        print("\n── 끝까지 풀린다 ──")
        for _ in range(5):
            if pg.is_hidden("#q-choice"):
                pg.locator("#slider").focus()
                for _ in range(6):
                    pg.keyboard.press("ArrowRight")
            else:
                pg.locator("#q-choice button").first.click()
            pg.click("#btn-next")
        pg.wait_for_selector("#view-result:not([hidden])", timeout=10000)
        ok(pg.inner_text("#score").strip(), "점수가 나온다",
           pg.inner_text("#score").replace("\n", ""))
        ok(len(pg.locator("#cards .card").all()) == 5, "결과 카드가 다섯 장")
        ok(not pg.is_hidden("#caveat"), "「이 데이터의 한계」가 결과에 보인다",
           pg.inner_text("#caveat")[:50].replace("\n", " "))

        print("\n── 남이 하는 짓 ──")
        pg.goto(f"{B}/?t=없는주제", wait_until="networkidle")
        ok(not pg.is_hidden("#view-home"), "없는 주제를 부르면 목록으로 떨어진다")
        pg.goto(f"{B}/?t=quakes&s=62&g=감이 좋은 편", wait_until="networkidle")
        ok(not pg.is_hidden("#shared-banner"), "공유 링크면 친구 점수가 뜬다",
           pg.inner_text("#shared-banner")[:40])
        ok(not pg.is_hidden("#view-home"),
           "공유 링크는 바로 풀리지 않고 목록을 보여 준다")

        print("\n── 열 주제가 다 열리나 ──")
        import json
        ids = [t["id"] for t in json.loads(
            (ROOT / "topics.json").read_text(encoding="utf-8"))["topics"]]
        못연 = []
        for tid in ids:
            pg.goto(f"{B}/?t={tid}", wait_until="networkidle")
            try:
                pg.wait_for_selector("#view-quiz:not([hidden])", timeout=6000)
                if not pg.inner_text("#q-text").strip():
                    못연.append(tid)
            except Exception:
                못연.append(tid)
        ok(not 못연, f"주제 {len(ids)}개가 다 열린다",
           f"{못연}" if 못연 else f"{len(ids)}/{len(ids)}")

        print("\n── 화면 ──")
        for w, 이름 in ((390, "폰"), (1440, "데스크톱")):
            pg.set_viewport_size({"width": w, "height": 900})
            pg.goto(B, wait_until="networkidle")
            sw, iw = pg.evaluate(
                "[document.documentElement.scrollWidth, window.innerWidth]")
            ok(sw <= iw + 1, f"{이름}({w}) 에서 가로로 안 밀린다", f"{sw} ≤ {iw}")

        진짜 = [e for e in 오류 if "/api/comment" not in e and "501" not in e]
        ok(not 진짜, "콘솔 오류가 없다",
           f"{진짜[:2]}" if 진짜 else "촌평 501(로컬엔 함수가 없다)만")
        b.close()

    bad = len(결과) - sum(결과)
    print(f"\n{sum(결과)}/{len(결과)} 지킴")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
