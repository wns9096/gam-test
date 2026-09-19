# -*- coding: utf-8 -*-
"""**배포된 주소**를 대고 점검한다. 로컬 점검(tools/점검.py)과 다른 것을 본다.

    python tools/배포점검.py
    python tools/배포점검.py https://다른주소.vercel.app

★ 왜 따로 있나. tools/점검.py 는 **내 폴더**를 본다. 배포는 내 폴더가
  아니다 — .vercelignore 가 무엇을 뺐는지, 환경변수가 들어갔는지,
  함수가 실제로 도는지는 주소를 열어 봐야만 안다.
  실제로 여기서 갈렸다. 로컬은 촌평이 1.1초에 오는데 배포본은
  {"comment": null} 이었다.

★ 걸렸던 것 하나를 검사로 박아 둔다. 배포 직후 화면에 나오는 주소
      gam-test-<해시>-<팀>.vercel.app
  는 **배포 하나를 가리키는 주소**라 Vercel 로그인을 요구한다(302).
  만든 사람 브라우저에서는 쿠키가 있어 그냥 열려서, 남한테 보내기
  전까지 모른다. 그래서 「로그인 없이 열리는가」를 검사한다.

★ 키는 한 글자도 안 읽는다. 지문(sha256 앞 8자리)만 견준다.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1
        else "https://gam-test-ebon.vercel.app").rstrip("/")
결과: list[bool] = []


def ok(cond, 라벨, 상세=""):
    결과.append(bool(cond))
    print(f"  [{'지킴' if cond else '걸림'}] {라벨}" + (f"  — {상세}" if 상세 else ""))


def 연다(path, data=None, follow=True):
    """(상태코드, 본문, 최종주소). 따라가지 않으면 302 를 그대로 본다."""
    # ★ 한글 파일명을 그대로 넣으면 urllib 가 UnicodeEncodeError 로 터진다.
    #   그걸 상태코드 0 으로 받아 「404 가 아니다 = 걸림」으로 셌다.
    #   **오류를 실패로 읽는 검사는 검사가 아니다.** 그래서 먼저 인코딩하고,
    #   아래에서 0(못 물어봄)과 404(없음)를 갈라 센다.
    url = f"{BASE}/{urllib.parse.quote(path.lstrip('/'))}"
    req = urllib.request.Request(
        url, data=data, method="POST" if data else "GET",
        headers={"Content-Type": "application/json"} if data else {})
    opener = (urllib.request.build_opener() if follow
              else urllib.request.build_opener(안따라감))
    try:
        with opener.open(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.url
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), url
    except Exception as e:
        return 0, f"{type(e).__name__}", url


class 안따라감(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def main() -> int:
    print(f"배포본을 연다 — {BASE}\n")

    print("── 남이 열 수 있는가 ──")
    code, body, _ = 연다("/", follow=False)
    ok(code in (200, 308), "로그인 없이 열린다",
       f"{code}" + ("  ← 배포 하나를 가리키는 주소다. Production 주소를 써야 한다"
                    if code == 302 else ""))
    code, home, _ = 연다("/")
    ok("<title>" in home and "감 테스트" in home, "앱 화면이 나온다",
       f"{len(home):,}자")

    print("\n── 올라간 것 · 안 올라간 것 ──")
    for p in ("style.css", "app.js", "topics.json"):
        c, b, _ = 연다(p)
        ok(c == 200, f"{p} 가 있다", f"{c} · {len(b):,}자")
    for p in ("tools/build_topics.py", "data/raw/quakes.geojson",
              "tools/검산.py"):
        c, b, _ = 연다(p)
        ok(c == 404, f"{p} 는 안 올라갔다",
           f"{c}" if c else f"물어보지도 못했다 — {b}")

    print("\n── 배포본이 내 폴더와 같은가 ──")
    # ★ 「밀었는데 안 바뀌었다」를 잡는 자리다. 빌드가 실패해도 이전
    #   배포가 계속 떠 있으므로, 열어 보면 멀쩡해 보인다.
    idx = json.loads(연다("topics.json")[1])["topics"]
    ok(len(idx) == 10, "주제가 열 개다", f"{len(idx)}개")
    다름 = []
    for t in idx:
        c, b, _ = 연다(f"topics/{t['id']}.json")
        내것 = (ROOT / "topics" / f"{t['id']}.json").read_text(encoding="utf-8")
        if c != 200 or json.loads(b) != json.loads(내것):
            다름.append(t["id"])
    ok(not 다름, "열 주제 파일이 내 폴더와 한 글자도 안 다르다",
       f"{다름}" if 다름 else "10/10")

    print("\n── 키가 화면에서 보이나 ──")
    샘 = [p for p in ("/", "app.js", "style.css")
          if re.search(r"AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-]{20,}",
                       연다(p)[1])]
    ok(not 샘, "브라우저가 받는 파일에 키가 없다",
       f"{샘}" if 샘 else "index · app.js · style.css 셋 다 깨끗")

    print("\n── 함수가 도는가 ──")
    c, b, _ = 연다("api/comment")
    상태 = json.loads(b) if c == 200 and b.startswith("{") else {}
    ok(상태.get("ok"), "함수가 살아 있다", f"{c}")
    ok(상태.get("key"), "환경변수가 들어갔다",
       "안 들어갔으면 Save 만 하고 Redeploy 를 안 한 것이다")
    ok(상태.get("ws") is False, "키에 공백이 안 딸려왔다",
       "붙여넣기가 줄바꿈을 끌고 오면 키는 있는데 400 이 난다")

    env = ROOT.parent / "proposal-bench" / ".env.local"
    if env.exists():
        m = re.search(r'^\s*GEMINI_API_KEY\s*=\s*["\']?([^"\'\r\n#]+)',
                      env.read_text(encoding="utf-8", errors="replace"), re.M)
        # ★ 줄 앵커(^)가 없으면 주석에 적힌 «예) AIzaSy...» 를 키로 읽는다.
        #   실제로 그래서 「키가 무효다」라는 틀린 결론을 한 번 냈다.
        내지문 = hashlib.sha256(m.group(1).strip().encode()).hexdigest()[:8] if m else None
        ok(내지문 and 내지문 == 상태.get("fp"),
           "배포에 들어간 키가 내 손의 키와 같다",
           f"내 {내지문} · 배포 {상태.get('fp')}")
    else:
        print("  [넘김] 손에 키 파일이 없어 지문은 못 견준다")

    print("\n── 촌평이 실제로 오는가 ──")
    보냄 = {"score": 62, "grade": "감이 좋은 편", "topic": "지진은 얼마나 자주",
            "directions": ["맞힘", "높게", "틀림", "높게", "틀림"]}
    c, b, _ = 연다("api/comment", json.dumps(보냄).encode())
    답 = json.loads(b) if c == 200 and b.startswith("{") else {}
    ok(답.get("comment"), "촌평이 온다",
       f"까닭 {답.get('reason')}" if not 답.get("comment")
       else f"「{답['comment'][:40]}…」 별명 {답.get('nickname')}")

    if 답.get("comment"):
        # ★ 프롬프트가 「숫자를 새로 만들지 마라」고 시킨다. 시켰다고 지킨
        #   것은 아니다. 보낸 숫자(62)말고 다른 수가 나오면 지어낸 것이다.
        수 = set(re.findall(r"\d+", 답["comment"] + 답.get("nickname", "")))
        지어냄 = 수 - {"62"}
        ok(not 지어냄, "촌평이 없는 숫자를 지어내지 않았다",
           f"지어낸 수 {sorted(지어냄)}" if 지어냄
           else f"쓴 수 {sorted(수) or '없음'} — 보낸 점수 말고는 없다")
        ok("지진" in 답["comment"] or "흔들" in 답["comment"] or "땅" in 답["comment"],
           "푼 주제 이야기를 한다",
           "topic 을 안 쓰면 엉뚱한 앱 이야기가 돌아온다")

    bad = len(결과) - sum(결과)
    print(f"\n{sum(결과)}/{len(결과)} 지킴")
    if bad:
        print("걸린 것이 다음에 할 일이다. Vercel → Deployments → Logs 도 본다.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
