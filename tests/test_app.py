from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from az_job_radar.app import create_app, format_salary
from az_job_radar.gate import COOKIE_NAME, PreviewGate
from az_job_radar.models import Vacancy

GATE = PreviewGate(user="reviewer", password="letmein", secret="test-secret")
HTML = {"accept": "text/html"}

VACANCIES = [
    Vacancy(
        source="boss.az",
        external_id="1",
        title="Python Developer",
        company="Acme",
        url="https://boss.az/vacancies/1",
        published_on=date(2026, 10, 1),
        salary_min=Decimal("1500"),
        salary_max=Decimal("2000"),
    ),
    Vacancy(
        source="jobsearch.az",
        external_id="2",
        title="<b>React</b> Engineer",
        company="Beta",
        url="https://jobsearch.az/vacancies/2",
        published_on=date(2026, 10, 3),
    ),
    Vacancy(source="jobsearch.az", external_id="3", title="Go Dev", company="Gamma", url="u"),
]


class FakeFetch:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> list[Vacancy]:
        self.calls += 1
        return VACANCIES


@pytest.fixture
def fetch() -> FakeFetch:
    return FakeFetch()


@pytest.fixture
def open_client(fetch: FakeFetch) -> TestClient:
    return TestClient(create_app(fetch=fetch))


@pytest.fixture
def gated_client(fetch: FakeFetch) -> TestClient:
    return TestClient(create_app(fetch=fetch, preview_gate=GATE), follow_redirects=False)


def login(client: TestClient, password: str = "letmein", next_url: str = "/"):
    return client.post(
        "/login",
        content=f"username=reviewer&password={password}&next={next_url}",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


def test_health(open_client: TestClient):
    assert open_client.get("/health").json() == {"status": "ok"}


def test_vacancies_are_sorted_newest_first(open_client: TestClient):
    body = open_client.get("/vacancies").json()
    assert body["count"] == 3
    uids = [item["uid"] for item in body["items"]]
    assert uids == ["jobsearch.az:2", "boss.az:1", "jobsearch.az:3"]
    assert body["items"][1]["salary_min"] == 1500.0


def test_vacancies_filter_by_source(open_client: TestClient):
    body = open_client.get("/vacancies", params={"source": "boss.az"}).json()
    assert [item["uid"] for item in body["items"]] == ["boss.az:1"]


def test_results_are_cached(open_client: TestClient, fetch: FakeFetch):
    open_client.get("/vacancies")
    open_client.get("/")
    assert fetch.calls == 1


def test_dashboard_escapes_html(open_client: TestClient):
    page = open_client.get("/").text
    assert "3 vacancies" in page
    assert "&lt;b&gt;React&lt;/b&gt; Engineer" in page
    assert "<b>React</b>" not in page


def test_format_salary():
    assert format_salary(VACANCIES[0]) == "1,500 – 2,000 AZN"
    assert format_salary(VACANCIES[1]) == ""


def test_gate_redirects_browser_to_login(gated_client: TestClient):
    response = gated_client.get("/vacancies", headers=HTML)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/vacancies"


def test_gate_returns_401_for_api_clients(gated_client: TestClient):
    assert gated_client.get("/vacancies").status_code == 401
    assert gated_client.get("/docs").status_code == 401


def test_gate_keeps_health_open(gated_client: TestClient):
    assert gated_client.get("/health").status_code == 200


def test_login_flow(gated_client: TestClient):
    assert gated_client.get("/login").status_code == 200

    response = login(gated_client, next_url="/vacancies")
    assert response.status_code == 303
    assert response.headers["location"] == "/vacancies"
    assert COOKIE_NAME in response.cookies

    assert gated_client.get("/vacancies").status_code == 200

    gated_client.get("/logout")
    gated_client.cookies.clear()
    assert gated_client.get("/vacancies").status_code == 401


def test_wrong_password_is_rejected(gated_client: TestClient):
    response = login(gated_client, password="nope")
    assert response.status_code == 401
    assert "Wrong username or password" in response.text
    assert COOKIE_NAME not in response.cookies


def test_login_ignores_external_next(gated_client: TestClient):
    response = login(gated_client, next_url="//evil.example")
    assert response.headers["location"] == "/"


def test_service_token_passes_gate(gated_client: TestClient):
    response = gated_client.get("/vacancies", headers={"x-preview-token": "test-secret"})
    assert response.status_code == 200
    assert gated_client.get("/vacancies", headers={"x-preview-token": "wrong"}).status_code == 401


def test_token_validation():
    token = GATE.make_token(now=1000)
    assert GATE.token_is_valid(token, now=2000)
    assert not GATE.token_is_valid(token, now=10**10)
    assert not GATE.token_is_valid(token.replace(".", ".x"), now=2000)
    assert not GATE.token_is_valid("garbage")


def test_gate_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PREVIEW_USER", raising=False)
    monkeypatch.delenv("PREVIEW_PASSWORD", raising=False)
    assert PreviewGate.from_env() is None

    monkeypatch.setenv("PREVIEW_USER", "a")
    monkeypatch.setenv("PREVIEW_PASSWORD", "b")
    monkeypatch.setenv("PREVIEW_SECRET", "c")
    assert PreviewGate.from_env() == PreviewGate(user="a", password="b", secret="c")
