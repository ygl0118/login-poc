"""確定性 mock 驗證：以與 swag.live 相同 selector / 多步流程的 mock 登入頁，
分兩段驗證（不依賴正式站 GeeTest，CI 穩定可重現）：

  A. 前段登入行為      —— 開頁 → landing 登入鈕 → 帳密表單 → 填入 → 送出（登入動作本身）
  B. 登入後行為（成功）—— 條件 5：右上角頭像 + 顯示登入帳號
  C. 登入後行為（失敗）—— 條件 4（反向）：錯誤密碼 → 紅字「帳號/密碼錯誤」

正式站登入成功後才看得到的條件 4/5 因 GeeTest anti-bot 無法端到端達成（實測 0/9），
故在此以 mock 確定性驗證，並留存證據截圖。
"""
import pathlib

import config

_RESULTS = pathlib.Path(__file__).resolve().parent.parent / "test-results"


def _evidence(page, name):
    _RESULTS.mkdir(exist_ok=True)
    path = _RESULTS / name
    page.screenshot(path=str(path))
    return path


# ---------- A. 前段登入行為 ----------
def test_login_flow_mock(mock_login_page):
    """前段登入行為：開頁 → 找到登入入口 → 進帳密表單 → 填入帳密 → 送出，登入動作完成。"""
    lp = mock_login_page
    lp.open()  # enter_from_landing()（條件1）+ choose_password_login()（條件2）內含斷言
    assert lp.login_form_visible(), "FAIL - 未進入帳號密碼登入表單"
    lp.login(config.USERNAME, config.PASSWORD)
    lp.expect_logged_in()  # 送出後登入表單關閉 = 登入動作完成
    print("PASS - 前段登入行為：開頁 → 帳密登入表單 → 填入 → 送出 完成")


# ---------- B. 登入成功後行為（條件 5）----------
def test_post_login_success_mock(mock_login_page):
    """登入成功後行為：多重訊號 + 條件 5（右上角頭像 + 顯示登入帳號）。"""
    lp = mock_login_page
    lp.open()
    lp.login(config.USERNAME, config.PASSWORD)
    lp.expect_logged_in()

    # 多重訊號降低偽陽性
    assert lp.member_indicator_visible(), "FAIL - 未出現登入後的會員元素（個人中心）"
    assert lp.auth_token() is not None, "FAIL - 未取得登入後的 token cookie"
    # 條件 5：右上角頭像 + 顯示登入帳號
    assert lp.avatar_visible(), "FAIL - 右上角未顯示頭像"
    assert lp.logged_in_account() == config.USERNAME, (
        f"FAIL - 顯示的帳號名稱不符：期望 {config.USERNAME}，實得 {lp.logged_in_account()}"
    )

    path = _evidence(lp.page, "login_success_evidence.png")
    print(f"PASS - 條件5 通過：登入後右上角頭像 + 帳號名 {lp.logged_in_account()}（證據：{path}）")


# ---------- C. 登入失敗後行為（條件 4，反向）----------
def test_post_login_failure_mock(mock_login_page):
    """登入失敗後行為（反向）：錯誤密碼 → 維持未登入 + 紅字「帳號/密碼錯誤」（條件 4）。"""
    lp = mock_login_page
    lp.open()
    lp.login(config.USERNAME, config.WRONG_PASSWORD)

    # 不應登入成功
    assert lp.login_form_visible(), "FAIL - 錯誤密碼竟然登入成功（應維持在登入頁）"
    assert lp.auth_token() is None, "FAIL - 錯誤密碼竟然取得了 token"
    assert not lp.avatar_visible(), "FAIL - 登入失敗卻顯示了頭像"
    # 條件 4：出現紅字錯誤訊息「帳號/密碼錯誤」
    err = lp.error_message()
    assert "帳號/密碼錯誤" in err, f"FAIL - 未出現預期的紅字錯誤訊息，實得：{err!r}"

    path = _evidence(lp.page, "login_fail_evidence.png")
    print(f"PASS - 條件4 通過：錯密紅字「{err}」（證據：{path}）")
