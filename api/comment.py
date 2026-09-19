# -*- coding: utf-8 -*-
"""Gemini 촌평 — Vercel 서버리스 함수.

이 앱에서 서버가 필요한 유일한 자리다. **키를 숨기기 위해서** 존재한다.
키를 app.js 에 적으면 브라우저에서 그대로 보인다.

  받는 것   {"score": 62, "grade": "감이 좋은 편", "topic": "지진은 얼마나 자주",
             "directions": ["맞힘", "높게", "틀림", "높게", "틀림"]}
  주는 것   {"comment": "...", "nickname": "..."}

**숫자를 보내지 않는다.** 방향만 보낸다 — 숫자를 주면 그 숫자로 새 숫자를
만들어낸다. 점수·등급·오차는 전부 브라우저가 이미 계산했다.

키가 없거나 호출이 실패하면 {"comment": null} 을 200 으로 돌려준다.
**앱은 촌평 없이도 그대로 돈다.**

외부 라이브러리를 쓰지 않는다 (requirements.txt 가 필요 없다).
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

# AI Studio(aistudio.google.com)에서 지금 쓸 수 있는 모델 이름으로 맞춘다.
# 모델 이름과 무료 한도는 자주 바뀐다 — 교안의 이름을 그대로 믿지 말 것.
#
# ★ 실제로 그랬다. 원래 적혀 있던 gemini-2.5-flash 는 **404** 다.
#   models 목록에는 이름이 나오는데 v1beta 로 부르면 없다고 한다. 그런데
#   이 함수는 무엇이 실패하든 {"comment": null} 을 돌려주므로, 그대로
#   배포하면 촌평이 **조용히 영영 안 뜬다.** 화면은 멀쩡해 보인다.
#   그래서 (1) 부를 수 있는 것을 직접 불러 보고 고르고, (2) 실패하면
#   까닭을 로그에 한 줄 남긴다. 조용히 꺼지는 것을 만들지 않는다.
#
#   불러 본 결과 (2026-09-19)
#     gemini-2.5-flash        404
#     gemini-2.5-flash-lite   404
#     gemini-3.5-flash        빈 응답 (생각 토큰이 200자 한도를 다 먹는다)
#     gemini-3.5-flash-lite   1.3초 · 정상
#     gemini-flash-lite-latest 1.4초 · 정상   ← 별칭이라 이름이 바뀌어도 산다
#
#   이름을 박으면 재현은 되지만 어느 날 404 가 된다(위가 그 예다).
#   별칭은 말이 바뀔 수 있지만 안 죽는다. 조용히 죽는 쪽이 더 나쁘다.
MODEL = "gemini-flash-lite-latest"
ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
            "models/{model}:generateContent")
TIMEOUT = 6

# ★ 앱은 topic 을 같이 보내는데(app.js) 이 함수가 받아서 버리고 있었다.
#   그리고 프롬프트는 이 앱이 아닌 다른 앱('입사 첫날 테스트') 이야기를
#   하고 있었다. 그래서 지진 문제를 풀었는데 「월급 계산할 때는…」 같은
#   촌평이 돌아왔다. 보내 준 것을 안 쓰면 안 보낸 것과 같다.
PROMPT = """너는 '감 테스트' 라는 퀴즈 앱의 촌평 담당이다.

사용자가 방금 「{topic}」 주제를 풀었다. 공개 데이터에서 계산한 숫자를
슬라이더와 택1로 맞히는 퀴즈다. 결과는 이렇다.

  점수: {score}점 ({grade})
  문항별로 어느 방향으로 빗나갔는지: {directions}

  '높게' = 실제보다 크게 잡음, '낮게' = 실제보다 작게 잡음,
  '비슷' = 거의 맞음, '맞힘'/'틀림' = 객관식

규칙
- 두 문장 이내로 짧게. 존댓말.
- **숫자를 새로 만들지 마라.** 위에 없는 수치를 쓰면 안 된다.
- 어느 방향으로 치우쳤는지를 짚고, 그 주제에 빗대 가볍게 말한다.
- 비꼬거나 훈계하지 않는다. 읽고 웃을 수 있게.
- 마지막 줄에 별명을 하나 붙인다. 6글자 이내.

형식(JSON 만 출력):
{{"comment": "두 문장", "nickname": "별명"}}"""


def _ask(score, grade, directions, topic=""):
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    # ★ .strip() 이 있는 까닭. 대시보드 입력칸에 붙여넣으면 줄바꿈이나
    #   공백이 끝에 붙는 일이 흔하다. 그러면 키는 «있는데» 400 이 난다.
    if not key:
        return None                      # 키가 없으면 조용히 건너뛴다

    body = {
        "contents": [{
            "parts": [{
                "text": PROMPT.format(score=score, grade=grade,
                                      topic=topic or "숫자 감각",
                                      directions=", ".join(directions))
            }]
        }],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 200,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        ENDPOINT.format(model=MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        out = json.loads(r.read().decode("utf-8"))
    text = out["candidates"][0]["content"]["parts"][0]["text"]
    got = json.loads(text)
    return {"comment": str(got.get("comment", ""))[:300],
            "nickname": str(got.get("nickname", ""))[:20]}


def _fp(key):
    """키의 **지문**. 앞 8자리 해시다.

    ★ 왜 이것을 내보내나. 「키를 넣었는데 촌평이 안 뜬다」 를 밖에서
      가릴 방법이 없었다. 길이나 앞글자를 내보내면 그건 키 조각이다.
      해시는 되돌릴 수 없고, 그러면서 **내 손의 키와 같은 것인지**는
      말해 준다. 로컬에서 같은 해시를 찍어 견주면 끝난다.
    """
    return hashlib.sha256(key.encode()).hexdigest()[:8] if key else None


def _reason(e):
    """왜 안 나왔는지를 **한 낱말로**. 키도 사용자 답도 안 담는다.

    ★ 원래는 stderr 에만 적었다. 그런데 그것을 보려면 Vercel 대시보드에
      들어가야 한다 — 즉 만든 사람만 볼 수 있고, 그 사람도 안 들어가면
      모른다. 조용히 꺼지지 않게 하려고 로그를 달았는데, 로그는 여전히
      «찾아가야 보이는 것»이었다. 그래서 응답에도 싣는다.
      화면은 이 값을 안 쓴다 — 촌평 자리는 그냥 비어 있다.
    """
    if isinstance(e, urllib.error.HTTPError):
        try:
            d = json.loads(e.read().decode("utf-8", "replace"))
            return f"HTTP{e.code}:{d.get('error', {}).get('status', '')}"[:40]
        except Exception:
            return f"HTTP{e.code}"
    return type(e).__name__


class handler(BaseHTTPRequestHandler):
    def _send(self, payload, code=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            got = _ask(int(req.get("score", 0)),
                       str(req.get("grade", "")),
                       [str(x) for x in req.get("directions", [])][:10],
                       str(req.get("topic", ""))[:60])
            self._send(got or {"comment": None, "reason": "NO_KEY"})
        except Exception as e:
            # ★ 앱은 멈추지 않는다. 다만 **조용히** 꺼지지도 않는다 —
            #   왜 안 떴는지를 Vercel Logs 에 한 줄 남긴다. 모델 이름이
            #   죽으면 화면은 멀쩡하고 촌평만 영영 안 뜨는데, 로그가
            #   없으면 그것을 알 길이 없다.
            #   키도 사용자 답도 안 적는다 — 모델 이름과 오류 종류만.
            까닭 = _reason(e)
            print(f"[comment] {MODEL} 실패: {까닭}", file=sys.stderr)
            self._send({"comment": None, "reason": 까닭})

    def do_GET(self):
        """앱은 안 쓴다. **사람이 배포를 확인하려고** 있는 자리다.

        키가 들어갔는지, 들어간 키가 내 손의 키와 같은 것인지를
        키를 보지 않고 확인한다.
        """
        raw = os.environ.get("GEMINI_API_KEY") or ""
        key = raw.strip()
        self._send({"ok": True,
                    "key": bool(key),
                    "fp": _fp(key),          # 지문. 키는 되돌릴 수 없다
                    "ws": raw != key,        # 붙여넣다 공백이 딸려왔나
                    "model": MODEL})
