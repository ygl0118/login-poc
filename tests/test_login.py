"""真實站台（swag.live）端到端登入測試（需 -m live 顯式開啟）。

執行：pytest tests/test_login.py -m live -v -s

實測結論：swag.live 在送出登入後以 GeeTest v4 滑塊驗證碼作為反自動化控制，啟發式解題
實測 0/9（見 README）。故真實站驗證到「觸發 GeeTest」為止：
  - 條件 1（首頁登入鈕）、2（帳號密碼登入）、3（觸發 GeeTest）→ 真實站明確驗證 PASS
  - 條件 4（紅字錯誤）、5（頭像 + 帳號名）→ 改於 tests/test_login_mock.py 以確定性 mock 驗證
反向（錯誤密碼不應登入）在真實站亦可驗證（不需破解驗證碼）。
"""
import pytest

import config

pytestmark = pytest.mark.live


def test_login_flow_until_captcha_live(login_page):
    """逐步驗證真實站可達範圍：條件 1 → 2 → 3。"""
    lp = login_page
    lp.goto()

    # 條件 1：首頁找到並點擊「帳號註冊 / 登入」
    lp.enter_from_landing()
    print("PASS - 條件1：找到並點擊『帳號註冊 / 登入』")

    # 條件 2：找到「帳號密碼登入」並進入帳密表單
    lp.choose_password_login()
    print("PASS - 條件2：進入『帳號密碼登入』表單")

    # 條件 3：填入帳密送出後觸發 GeeTest 驗證碼
    lp.login(config.USERNAME, config.PASSWORD)
    assert lp.geetest_triggered(), "FAIL - 送出後未觸發 GeeTest 驗證碼"
    print("PASS - 條件3：填入帳密後觸發 GeeTest 滑塊驗證碼")


def test_login_wrong_password_live(login_page):
    """反向：錯誤帳密在任何情況下都不應登入成功。"""
    lp = login_page
    lp.open()
    lp.login(config.USERNAME, config.WRONG_PASSWORD)

    assert lp.login_form_visible(), "FAIL - 錯誤密碼竟然登入成功"
    assert lp.auth_token() is None, "FAIL - 錯誤密碼竟然取得 session token"
    print("PASS - Login failed as expected")
