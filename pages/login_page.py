"""SWAG (swag.live) 登入頁的 Page Object（data-testid 為主、fallback 為輔的定位策略）。

真實登入流程（經實際探查）：
  1. 進站後出現 landing 年齡牆，需點「帳號註冊 / 登入」開啟登入彈窗
  2. 彈窗預設為「手機/Email + 驗證碼」，需切換到「帳號密碼登入」
  3. 填入帳號 / 密碼後點「登入」送出
  4. 送出後出現 GeeTest v4 滑塊驗證碼（商用反自動化機制，實測無法可靠破解）

因此本框架：真實站驗證到「觸發 GeeTest」為止（條件 1~3）；登入成功後才看得到的
「紅字錯誤訊息（條件 4）」與「頭像 + 帳號名（條件 5）」改由 tests/test_login_mock.py
以與真實站相同 selector 的確定性 mock 驗證。

定位策略：以 **data-testid** 作為測試契約（不受文案翻譯 / 樣式 / DOM 改版影響），每個元素
另附 **fallback**（現有 id / role+文字 / 經比對真實 DOM 的屬性）；待前端補上 test-id 即可移除。
所有定位器集中於此，測試只描述意圖；等待一律用 Playwright 自動等待 / expect，不用 sleep。
"""
from playwright.sync_api import Locator, Page, expect

import config
from pages.base_page import BasePage


class LoginPage(BasePage):
    # --- 定位器契約：key -> data-testid（首選）---
    TESTID = {
        "landing_enter": "landing-login-entry",
        "switch_to_password": "switch-password-login",
        "username": "login-username",
        "password": "login-password",
        "submit": "login-submit",
        "member": "member-menu",
        "avatar": "user-avatar",        # 登入後右上角頭像
        "account_name": "account-name", # 登入後顯示的帳號名稱
    }
    # --- fallback：頁面尚無 data-testid 時改用（策略, 值）---
    #   css        -> page.locator(css)
    #   role       -> page.get_by_role(role, name=...)
    #   role_exact -> page.get_by_role(role, name=..., exact=True)
    FALLBACK = {
        "landing_enter": ("role", ("button", "帳號註冊 / 登入")),
        "switch_to_password": ("role", ("button", "帳號密碼登入")),
        "username": ("css", "#username-form"),
        "password": ("css", "#password-form"),
        "submit": ("role_exact", ("button", "登入")),
        "member": ("css", "#user-menu"),
        # 真實站 swag.live 登入後的頭像 / 帳號名（已比對真實登入態 DOM 確認，供未來測試環境沿用）：
        #   頭像：<img alt="大頭貼">（MeAvatar，登出不存在）；帳號名：header <a href="/user/<id>">
        "avatar": ("css", "#user-avatar, [class*='MeAvatar'], img[alt='大頭貼']"),
        "account_name": ("css", "#account-name, header a[href^='/user/']:not([href='/user/null'])"),
    }
    GEETEST_BUTTON = ".geetest_btn"
    ERROR_HINT_RE = ["錯誤", "不正確", "失敗", "無效", "不存在", "incorrect", "invalid"]
    # 真正的登入態 cookie 名稱（排除 _ga / did_4 等第三方追蹤 cookie）
    AUTH_COOKIE_NAMES = ("token", "access_token", "auth", "session", "sessionid")

    def __init__(self, page: Page):
        super().__init__(page)

    # --- 定位器解析：優先 data-testid，找不到才用 fallback ---
    def _loc(self, key: str) -> Locator:
        testid = self.page.get_by_test_id(self.TESTID[key])
        if testid.count() > 0:
            return testid
        kind, val = self.FALLBACK[key]
        if kind == "css":
            return self.page.locator(val)
        role, name = val
        return self.page.get_by_role(role, name=name, exact=(kind == "role_exact"))

    @staticmethod
    def _any_visible(loc: Locator) -> bool:
        """同一 selector 常同時命中行動版與桌機版（其一隱藏），任一可見即算可見。"""
        for i in range(loc.count()):
            try:
                if loc.nth(i).is_visible():
                    return True
            except Exception:
                pass
        return False

    def _click_first_visible(self, loc: Locator) -> bool:
        """等待並點擊第一個『可見』的元素（真實站常有重複的隱藏節點）。找不到回 False。"""
        try:
            loc.first.wait_for(state="attached", timeout=config.DEFAULT_TIMEOUT)
        except Exception:
            return False
        for i in range(loc.count()):
            item = loc.nth(i)
            if item.is_visible():
                item.click()
                return True
        return False

    # --- 流程動作 ---
    def open(self):
        """進站並開啟『帳號密碼登入』表單（含條件 1、2 的明確驗證）。"""
        self.goto()
        self.enter_from_landing()       # 條件 1
        self.choose_password_login()    # 條件 2
        return self

    def enter_from_landing(self):
        """條件 1：首頁找到並點擊『帳號註冊 / 登入』按鈕；找不到即明確 FAIL。"""
        if not self._click_first_visible(self._loc("landing_enter")):
            raise AssertionError("FAIL - 首頁找不到『帳號註冊 / 登入』按鈕")
        return self

    def choose_password_login(self):
        """條件 2：點『帳號密碼登入』並等帳密表單出現（以表單出現作同步點，不用 sleep）。"""
        self._click_first_visible(self._loc("switch_to_password"))
        expect(self._loc("password")).to_be_visible(timeout=config.DEFAULT_TIMEOUT)
        return self

    def login(self, username: str, password: str):
        """填入帳號密碼並送出。"""
        self._loc("username").fill(username)
        self._loc("password").fill(password)
        self._loc("submit").first.click()
        return self

    def geetest_triggered(self, timeout: int = 8000) -> bool:
        """條件 3：送出後是否觸發 GeeTest 滑塊驗證碼（等待其渲染，不用 sleep）。"""
        try:
            self.page.wait_for_selector(self.GEETEST_BUTTON, state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    # --- 驗證用查詢 ---
    def login_form_visible(self) -> bool:
        loc = self._loc("password")
        return loc.count() > 0 and loc.first.is_visible()

    def member_indicator_visible(self) -> bool:
        return self._any_visible(self._loc("member"))

    def avatar_visible(self) -> bool:
        """條件 5：登入後右上角頭像是否可見（任一可見版本即可）。"""
        return self._any_visible(self._loc("avatar"))

    def logged_in_account(self) -> str:
        """條件 5：登入後顯示的帳號名稱；取第一個『可見且非佔位符』的文字。"""
        loc = self._loc("account_name")
        for i in range(loc.count()):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    name = (item.inner_text() or "").strip()
                    if name and name != "-":
                        return name
            except Exception:
                pass
        return ""

    def auth_token(self):
        """回傳登入後的 session / 驗證 cookie（若有）；忽略追蹤類 cookie。"""
        for c in self.page.context.cookies():
            if c["name"].lower() in self.AUTH_COOKIE_NAMES:
                return c
        return None

    def error_message(self) -> str:
        """條件 4：擷取登入失敗時的紅字錯誤提示文字（若有）。"""
        body = self.page.inner_text("body")
        for line in body.split("\n"):
            line = line.strip()
            if line and len(line) < 40 and any(k in line for k in self.ERROR_HINT_RE):
                return line
        return ""

    def expect_logged_in(self, timeout: int = None):
        """斷言登入成功：登入表單消失/隱藏（彈窗關閉）。失敗會拋出。"""
        expect(self._loc("password")).to_be_hidden(timeout=timeout or config.DEFAULT_TIMEOUT)
