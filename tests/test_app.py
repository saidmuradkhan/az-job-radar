from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from az_job_radar.app import create_app
from az_job_radar.dashboard import format_salary
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
    Vacancy(
        source="hellojob.az",
        external_id="9",
        title="Python developer",
        company="ACME MMC",
        url="https://hellojob.az/vacancies/9",
        published_on=date(2026, 9, 30),
        category="it",
        tags=("python", "django"),
        languages=("english",),
        experience_years=2,
        description="Python, Django, 2 il təcrübə, ingilis dili",
    ),
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
    assert uids == ["jobsearch.az:2", "hellojob.az:9", "jobsearch.az:3"]


def test_cross_site_copies_are_merged(open_client: TestClient):
    item = open_client.get("/vacancies").json()["items"][1]
    assert item["uid"] == "hellojob.az:9"
    assert item["tags"] == ["python", "django"]
    assert item["also_on"] == [{"source": "boss.az", "url": "https://boss.az/vacancies/1"}]


def test_vacancies_filters(open_client: TestClient):
    def uids(**params):
        body = open_client.get("/vacancies", params=params).json()
        return [item["uid"] for item in body["items"]]

    assert uids(category="it") == ["hellojob.az:9"]
    assert uids(tag=["python", "django"]) == ["hellojob.az:9"]
    assert uids(tag=["python", "java"]) == []
    assert uids(language="english", max_experience=3) == ["hellojob.az:9"]
    assert uids(max_experience=1) == ["jobsearch.az:2", "jobsearch.az:3"]
    assert uids(q="react") == ["jobsearch.az:2"]


def test_vacancies_include_facets(open_client: TestClient):
    body = open_client.get("/vacancies", params={"category": "it"}).json()
    assert body["facets"]["tags"] == [["python", 1], ["django", 1]]


def test_vacancies_pagination(open_client: TestClient):
    body = open_client.get("/vacancies", params={"per_page": 2, "page": 2}).json()
    assert body["count"] == 3
    assert [item["uid"] for item in body["items"]] == ["jobsearch.az:3"]


def test_bad_filter_value_is_rejected(open_client: TestClient):
    assert open_client.get("/vacancies", params={"max_experience": -1}).status_code == 422
    assert open_client.get("/vacancies", params={"min_salary": "abc"}).status_code == 422


def test_empty_form_fields_mean_no_filter(open_client: TestClient):
    response = open_client.get("/?q=&category=&max_experience=&min_salary=&city=")
    assert response.status_code == 200
    assert "3 vacancies" in response.text


def test_vacancy_detail(open_client: TestClient):
    body = open_client.get("/vacancies/hellojob.az:9").json()
    assert body["description"].startswith("Python, Django")
    assert body["also_on"][0]["source"] == "boss.az"
    assert open_client.get("/vacancies/nope:1").status_code == 404


def test_vacancies_filter_by_source(open_client: TestClient):
    body = open_client.get("/vacancies", params={"source": "boss.az"}).json()
    assert [item["uid"] for item in body["items"]] == ["hellojob.az:9"]
    body = open_client.get("/vacancies", params={"source": "jobsearch.az"}).json()
    assert [item["uid"] for item in body["items"]] == ["jobsearch.az:2", "jobsearch.az:3"]


def test_results_are_cached(open_client: TestClient, fetch: FakeFetch):
    open_client.get("/vacancies")
    open_client.get("/")
    assert fetch.calls == 1


def test_dashboard_escapes_html(open_client: TestClient):
    page = open_client.get("/").text
    assert "3 vacancies · 1 duplicate posts merged" in page
    assert "&lt;b&gt;React&lt;/b&gt; Engineer" in page
    assert "<b>React</b>" not in page


def test_dashboard_filters(open_client: TestClient):
    page = open_client.get("/", params={"category": "it", "tag": "python"}).text
    assert "1 vacancies" in page
    assert '<option value="it" selected>IT (1)</option>' in page
    assert 'name="tag" value="python" checked' in page
    assert "Also on" in page and "boss.az" in page
    assert "React" not in page


def test_dashboard_with_no_results(open_client: TestClient):
    page = open_client.get("/", params={"q": "nothing-like-this"}).text
    assert "No vacancies match these filters." in page


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
