"""Temporary login page that keeps the site private until it is ready for review."""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from html import escape
from urllib.parse import parse_qs, quote

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

COOKIE_NAME = "preview_session"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60
OPEN_PATHS = {"/health", "/login", "/logout"}


@dataclass(frozen=True)
class PreviewGate:
    user: str
    password: str
    secret: str

    @classmethod
    def from_env(cls) -> "PreviewGate | None":
        user = os.environ.get("PREVIEW_USER", "")
        password = os.environ.get("PREVIEW_PASSWORD", "")
        if not user or not password:
            return None
        secret = os.environ.get("PREVIEW_SECRET") or password
        return cls(user=user, password=password, secret=secret)

    def check_credentials(self, user: str, password: str) -> bool:
        user_ok = hmac.compare_digest(user.encode(), self.user.encode())
        password_ok = hmac.compare_digest(password.encode(), self.password.encode())
        return user_ok and password_ok

    def make_token(self, now: float | None = None) -> str:
        expires = int((now or time.time()) + COOKIE_MAX_AGE)
        return f"{expires}.{self._sign(expires)}"

    def token_is_valid(self, token: str, now: float | None = None) -> bool:
        expires, _, signature = token.partition(".")
        if not expires.isdigit():
            return False
        if int(expires) < (now or time.time()):
            return False
        return hmac.compare_digest(signature, self._sign(int(expires)))

    def allows(self, request: Request) -> bool:
        if request.url.path in OPEN_PATHS:
            return True
        service_token = request.headers.get("x-preview-token", "")
        if service_token and hmac.compare_digest(service_token, self.secret):
            return True
        return self.token_is_valid(request.cookies.get(COOKIE_NAME, ""))

    def _sign(self, expires: int) -> str:
        message = f"{self.user}:{expires}".encode()
        return hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()


def safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


async def gate_middleware(request: Request, call_next) -> Response:
    gate: PreviewGate | None = request.app.state.gate
    if gate is None or gate.allows(request):
        return await call_next(request)

    if request.method == "GET" and "text/html" in request.headers.get("accept", ""):
        target = quote(request.url.path, safe="/")
        return RedirectResponse(f"/login?next={target}", status_code=303)
    return JSONResponse({"detail": "Login required"}, status_code=401)


def login_page(next_url: str, error: bool = False, status_code: int = 200) -> HTMLResponse:
    message = '<p class="error">Wrong username or password.</p>' if error else ""
    html = LOGIN_HTML.format(next=escape(next_url, quote=True), message=message)
    return HTMLResponse(html, status_code=status_code)


async def show_login(request: Request) -> Response:
    return login_page(safe_next(request.query_params.get("next")))


async def submit_login(request: Request) -> Response:
    gate: PreviewGate | None = request.app.state.gate
    form = parse_qs((await request.body()).decode())
    user = form.get("username", [""])[0]
    password = form.get("password", [""])[0]
    next_url = safe_next(form.get("next", ["/"])[0])

    if gate is None:
        return RedirectResponse(next_url, status_code=303)
    if not gate.check_credentials(user, password):
        return login_page(next_url, error=True, status_code=401)

    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        gate.make_token(),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return response


async def logout(request: Request) -> Response:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


LOGIN_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Sign in · az-job-radar</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f4f5f7; margin: 0;
         min-height: 100vh; display: grid; place-items: center; color: #1f2328; }}
  form {{ background: #fff; padding: 2rem; border-radius: 12px; width: min(320px, 90vw);
          box-shadow: 0 4px 24px rgba(0, 0, 0, .08); display: grid; gap: .75rem; }}
  h1 {{ font-size: 1.2rem; margin: 0 0 .5rem; }}
  input {{ padding: .6rem; border: 1px solid #d0d7de; border-radius: 6px; font-size: 1rem; }}
  button {{ padding: .65rem; border: 0; border-radius: 6px; background: #1f6feb;
            color: #fff; font-size: 1rem; cursor: pointer; }}
  .error {{ color: #cf222e; margin: 0; font-size: .9rem; }}
  .hint {{ color: #656d76; font-size: .8rem; margin: 0; }}
</style>
</head>
<body>
<form method="post" action="/login">
  <h1>az-job-radar</h1>
  <p class="hint">This preview is private for now.</p>
  {message}
  <input type="hidden" name="next" value="{next}">
  <input name="username" placeholder="Username" autocomplete="username" required autofocus>
  <input name="password" type="password" placeholder="Password"
         autocomplete="current-password" required>
  <button type="submit">Sign in</button>
</form>
</body>
</html>
"""
