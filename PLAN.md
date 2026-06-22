# 測試方針（PLAN）

## 1. 目標
驗證 `swag.live` 的帳號密碼登入流程：
- 正向：正確帳密 → 登入成功（多重訊號斷言）。
- 反向：錯誤密碼 → 登入失敗（明確 FAIL / 不應取得登入態）。

## 2. 範圍與分層
| 層級 | 檔案 | 目的 | 穩定性 |
| --- | --- | --- | --- |
| 確定性層 | `tests/test_login_mock.py` | 驗證 POM 與斷言邏輯本身正確 | 高（CI 可重現） |
| 端到端層 | `tests/test_login.py` (`-m live`) | 對真實站走完整 UI 流程 | 受 anti-bot 影響 |

分層理由：正式站送出登入後有 **GeeTest v4 滑塊驗證碼**（反自動化控制，實測無法可靠破解）。
若把「程式是否正確」綁在「能否破解驗證碼」上，測試會變得不可靠。故以 mock（相同 selector）
確定性驗證登入成功後才可見的條件 4/5；真實站（`-m live`）則驗證可達範圍（條件 1/2/3 + 反向）。

## 3. 登入成功的判定（同步點與斷言）
送出後以「登入後才出現/消失的元素」作為同步點，而非固定秒數：
- (a) 登入表單（`#password-form`）消失 / 隱藏（彈窗關閉）。
- (b) 出現登入後才有的會員元素（`#user-menu` 個人中心）。
- (c) 取得 session token cookie（排除 `_ga` / `did_4` 等第三方追蹤 cookie）。

三者皆成立才判定成功，降低偽陽性（例如僅 URL 變更但實際出錯）。

## 4. 登入失敗的判定（反向）
- 登入表單仍在（未進入會員區）。
- 未取得 session token。
- 出現錯誤提示文字（關鍵字：錯誤 / 不正確 / 無效 / 不存在 …）。
任一條件不符即測試 FAIL。

## 5. 等待策略
全程使用 Playwright 自動等待 + `expect(...).to_be_visible / to_be_hidden`、
`locator.wait_for(state=...)`，**不使用 `time.sleep` 硬等**，兼顧穩定與速度。

## 6. 憑證與設定
帳密、BASE_URL、逾時、headless 等一律來自環境變數（`.env` / CI 注入），
`config.validate()` 在測試前檢查必要變數，缺漏即快速失敗。

## 7. 風險與已知限制
- **anti-bot 驗證碼**：正式站登入受 GeeTest 保護，自動化環境無法穩定通過（實測解題 0/9，
  重用登入態亦不可行）。故條件 4/5 改於 mock 確定性驗證；詳見 README。
- **頭像 / 帳號名 selector**：已比對**真實登入態 DOM** 確認（頭像 `img[alt='大頭貼']` / MeAvatar，
  帳號名 header `a[href^='/user/']`），寫在 `LoginPage.FALLBACK`；待測試環境驗證碼白名單即可
  直接於真實站套用、補上條件 5 的真實站斷言。
- **post-login session cookie 名稱**：以常見命名推測（`token`/`session`…）；可向後端確認後收斂。
