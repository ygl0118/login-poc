"""pytest fixtures：管理瀏覽器生命週期與測試隔離。

- browser 為 session 級（省去重複啟動成本）
- 每個測試使用獨立 context，cookie / session 互不污染
"""
import json
import pathlib

import pytest
from playwright.sync_api import Page, sync_playwright

import config
from pages.login_page import LoginPage

_RESULTS_DIR = pathlib.Path(__file__).parent / "test-results"


def _find_page(item) -> Page:
    """從測試所用的 fixtures 找出可截圖的 Page。"""
    for val in item.funcargs.values():
        if isinstance(val, Page):
            return val
        page = getattr(val, "page", None)
        if isinstance(page, Page):
            return page
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """任一測試於執行階段失敗時：自動截圖到 test-results/ 並印出明確 FAIL 訊息。"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = _find_page(item)
        if page is not None:
            _RESULTS_DIR.mkdir(exist_ok=True)
            path = _RESULTS_DIR / f"{item.name}_FAIL.png"
            try:
                page.screenshot(path=str(path), timeout=5000)
                print(f"\nFAIL - {item.name}：已存失敗截圖 {path}")
            except Exception as exc:  # 截圖失敗不應掩蓋原始錯誤
                print(f"\nFAIL - {item.name}：截圖失敗（{exc}）")

_MOCK_HTML = (pathlib.Path(__file__).parent / "mock" / "login_mock.html").read_text(
    encoding="utf-8"
)


@pytest.fixture(scope="session", autouse=True)
def _validate_config():
    """在任何測試開始前驗證設定，缺漏即快速失敗。"""
    config.validate()


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=config.HEADLESS,
        slow_mo=config.SLOW_MO,
    )
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    # 每個測試獨立 context，確保測試隔離
    context = browser.new_context(locale="zh-TW")
    context.set_default_timeout(config.DEFAULT_TIMEOUT)
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def login_page(page):
    return LoginPage(page)


@pytest.fixture
def mock_login_page(context):
    """以 route 攔截把 BASE_URL 換成本地 mock 登入頁，確定性地驗證 POM 與斷言。

    正確帳密由 config（環境變數）注入到 mock 頁，程式與頁面皆不寫死憑證。
    """
    creds = json.dumps({"username": config.USERNAME, "password": config.PASSWORD})
    context.add_init_script(f"window.__MOCK_CREDS__ = {creds};")

    def _handler(route):
        route.fulfill(status=200, content_type="text/html", body=_MOCK_HTML)

    # 攔截對登入站的主文件請求，回以 mock HTML
    context.route("**/*", lambda route: (
        _handler(route)
        if route.request.resource_type == "document"
        else route.continue_()
    ))
    page = context.new_page()
    yield LoginPage(page)
    page.close()
