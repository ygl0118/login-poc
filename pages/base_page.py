"""Page Object 基底類別：封裝共用的導頁與等待行為。

等待策略：一律使用 Playwright 內建的自動等待 / expect，不使用 time.sleep 硬等。
"""
from playwright.sync_api import Page

import config


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def goto(self, url: str = None, wait_until: str = "domcontentloaded", timeout: int = None):
        target = url or config.BASE_URL
        self.page.goto(target, wait_until=wait_until, timeout=timeout)
        return self

    @property
    def url(self) -> str:
        return self.page.url
