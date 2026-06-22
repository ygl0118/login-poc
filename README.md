# SWAG (swag.live) — 自動化登入測試框架

以 **Python + Playwright + pytest** 實作的登入流程自動化測試，採用 **Page Object Model**、
**環境變數管理憑證**、**Playwright 自動等待（不使用 sleep 硬等）**，並包含正向（登入成功）
與反向（錯誤密碼）測試，Console 以 `PASS - ... / FAIL - ...` 輸出。

> 測試目標：`https://swag.live/?lang=zh-TW`

## 專案結構

```
login-poc/
├── README.md
├── PLAN.md                   # 測試方針
├── manual_test_cases.md      # 對應的手動測試案例
├── Makefile                  # make setup / test / test-live（Python>=3.12）
├── requirements.txt
├── pytest.ini                # marker 設定（預設排除 live）
├── .env.example              # 環境變數範例（複製為 .env）
├── config.py                 # 設定載入 + validate() 快速失敗
├── conftest.py               # pytest fixtures（瀏覽器生命週期、mock 攔截、失敗截圖）
├── pages/                    # Page Object Model
│   ├── base_page.py
│   └── login_page.py         # swag.live 登入 POM（data-testid 為主 + fallback）
├── mock/
│   └── login_mock.html       # 與真實站相同 selector 的 mock 登入頁
└── tests/
    ├── test_login_mock.py    # 確定性驗證（CI 穩定）：前段登入行為 + 登入後行為(成功=條件5 / 失敗=條件4)
    └── test_login.py         # 真實站（-m live）：前段登入行為(條件1/2/3) + 反向
```

## 安裝與執行

```bash
python3 -m venv .venv && source .venv/bin/activate   # 需 Python >= 3.12
pip install -r requirements.txt
python -m playwright install chromium

# 設定帳密（不寫死在程式碼）
cp .env.example .env          # 編輯 .env 填入 LOGIN_USERNAME / LOGIN_PASSWORD

# 1) 確定性測試（mock）— CI 友善、穩定、快速（預設只跑這個，live 被排除）
pytest

# 2) 真實站測試（會連線 swag.live；驗證到觸發 GeeTest 為止 + 反向）
pytest tests/test_login.py -m live
```

也可用 Makefile（內含 Python ≥ 3.12 檢查）：

```bash
make setup       # 建立 .venv + 安裝相依（含 Playwright Chromium）
make test        # mock：前段登入行為 + 條件4 + 條件5（= make test-mock）
make test-live   # 真實站：前段登入行為(條件1/2/3) + 反向
make test-all    # mock + live；make clean 清環境
```

## 五項驗證條件對照

| # | 條件 | 在哪驗證 | 結果 |
| --- | --- | --- | --- |
| 1 | 首頁找到「帳號註冊 / 登入」按鈕 | 真實站 `test_login_flow_until_captcha_live` | ✅ PASS（`enter_from_landing()` 明確斷言，找不到即 FAIL） |
| 2 | 點擊後找到「帳號密碼登入」 | 真實站 同上 | ✅ PASS（`choose_password_login()`，以密碼欄出現作同步點） |
| 3 | 填完帳密觸發 GeeTest | 真實站 同上 | ✅ PASS（`geetest_triggered()` 斷言滑塊出現） |
| 4 | 錯密 → 紅字「帳號/密碼錯誤」 | mock `test_post_login_failure_mock` | ✅ PASS（斷言紅字 + 證據截圖 `test-results/login_fail_evidence.png`） |
| 5 | 登入成功 → 右上角頭像 + 顯示帳號 | mock `test_post_login_success_mock` | ✅ PASS（斷言頭像 + 帳號名 + 證據截圖） |

### 測試分層：前段登入行為 vs 登入後行為

每個情境拆成兩種測案，職責清晰：

| 類別 | 測案 | 驗證 |
| --- | --- | --- |
| **前段登入行為**（登入動作本身） | mock `test_login_flow_mock`、真實站 `test_login_flow_until_captcha_live` | 開頁 → 找登入入口 → 進帳密表單 → 填入 → 送出（真實站到觸發 GeeTest 為止＝條件 1/2/3） |
| **登入後行為（成功）** | mock `test_post_login_success_mock` | 條件 5：右上角頭像 + 顯示帳號 |
| **登入後行為（失敗，反向）** | mock `test_post_login_failure_mock`、真實站 `test_login_wrong_password_live` | 條件 4：紅字「帳號/密碼錯誤」（mock）；真實站驗未登入 + 未取得 token |

反向測試（錯誤密碼 → 預期 FAIL）同時存在於 mock（驗紅字＝條件 4）與真實站（驗未登入 + 未取得 token）。

## ⚠️ 關鍵發現：正式站受 GeeTest 反自動化驗證碼保護

實際探查 `swag.live` 的登入流程為：landing 年齡牆 →「帳號註冊 / 登入」→ 切換「帳號密碼登入」
→ 填帳密送出 → **跳出 GeeTest v4 滑塊拼圖驗證碼**。GeeTest 是商用 anti-bot 安全控制
（缺口比對之外還有行為軌跡分析、裝置指紋、多種題型輪替）。

> **實測無法在自動化環境穩定通過**：啟發式缺口偵測 + 人性化軌跡解題 **0/9**；
> 改走「重用真實 Chrome 登入態」也不可行（session 存於 IndexedDB，`storage_state` 經 CDP
> 匯出不含 origin 儲存；直接載入 profile 則導頁卡死）。**這是一項應回報的測試發現。**

因此本框架把「**程式是否正確**」與「**正式站是否擋自動化**」**解耦**：

- **真實站**（`test_login.py`，`-m live`）驗證到「觸發 GeeTest」為止 → 條件 1/2/3，以及反向（錯密不應登入）。
- **登入成功後才看得到的條件 4（紅字）、5（頭像+帳號名）**：改以 `mock/login_mock.html`
  （**與真實站相同的 selector 與多步流程**）+ Playwright `route` 攔截，**確定性**驗證並留存證據截圖。
- 條件 4/5 的真實站 selector 已依**實際登入態 DOM** 比對確認，寫在 `LoginPage.FALLBACK`；
  日後若有測試環境的驗證碼白名單，可直接沿用。

## 設計取捨（Design Decisions）

1. **Page Object Model**：定位器與頁面操作封裝於 `pages/login_page.py`，測試只描述意圖（open / login / 各種斷言查詢）。UI 改版時維護成本集中一處。
2. **定位策略：`data-testid` 為主、fallback 為輔**：以 test-id 作為測試契約，不受文案翻譯（本站有 `lang` 參數）、樣式或 DOM 改版影響。`LoginPage.TESTID` 為首選；`FALLBACK` 提供現有 id / role+文字（真實站尚無 test-id 走此路）。mock 頁採 data-testid，真實站走 fallback——同一套 POM 兩邊通用。
3. **憑證以環境變數管理，零硬編碼**：`python-dotenv` + `config.py` 集中讀取；`.env` 不進版控，CI 由 **GitHub Repository variables** 注入（見下）。`config.validate()` 在測試啟動前檢查必要變數，缺漏即「快速失敗」。
4. **等待策略：不使用 `sleep` 硬等**：全程用 Playwright 自動等待與 `expect(...).to_be_visible/to_be_hidden(timeout=...)`、`locator.wait_for(state=...)`，以「出現/消失的元素」作為同步點（例：以密碼欄出現確認已進入帳密表單）。
5. **多重斷言降低偽陽性**：登入成功同時驗證 (a) 登入表單消失、(b) 出現會員元素（個人中心）、(c) 取得 session token cookie（排除 `_ga`/`did_4` 等追蹤 cookie）、(d) 右上角頭像 + 帳號名；反向確認「未登入 + 未取得 token + 出現紅字錯誤」。
6. **確定性 mock 與真實站解耦**：正式站受 anti-bot 影響不可靠，故把「邏輯正確性」放到 mock（相同 selector）確定性驗證，CI 穩定可重現；真實站只驗證可達範圍。
7. **失敗即留證據**：`conftest.py` 的 pytest hook 在任一測試失敗時自動截圖到 `test-results/` 並印 `FAIL - …`；正/反向 mock 測試通過時也主動存證據截圖。
8. **測試隔離**：`browser` 為 session 級（省啟動成本），每個測試使用獨立 `context`，cookie/session 互不污染。

## 憑證管理（不進版控）

帳密一律來自環境變數，程式與 `.env.example` 皆**不含真實憑證**：

- **本機**：`cp .env.example .env` 後填入真實值；`.env` 已被 `.gitignore` 排除。
- **CI（GitHub Actions）**：由 **Repository variables**（Settings → Secrets and variables →
  Actions → Variables）設定 `LOGIN_USERNAME`、`LOGIN_PASSWORD`，workflow 以
  `${{ vars.* }}` 帶入 env（見 `.github/workflows/ci.yml`）。若需遮罩可改放 **Secrets** 並用 `${{ secrets.* }}`。

## CI

`.github/workflows/ci.yml`（push / PR / 手動觸發），Python 3.12 + pip 快取，兩個 job：

| Job | 內容 | 把關 |
| --- | --- | --- |
| **mock-tests** | `pytest`（預設排除 live）：前段登入行為 + 條件4 + 條件5 | **阻斷**（主要把關，穩定可重現） |
| **live-tests** | `pytest -m live`：真實站前段登入行為（條件1/2/3）+ 反向 | **非阻斷**（`continue-on-error`） |

- 帳密由 **Repository variables**（`${{ vars.LOGIN_USERNAME/PASSWORD }}`）注入。
- 兩個 job 都**每次上傳** `test-results/`（mock 的條件 4/5 證據截圖；失敗時另含 `*_FAIL.png`）。
- **為何 live 可上 CI**：live 只驗證到「觸發 GeeTest」為止（GeeTest 之後本就無法自動化），
  不依賴破解驗證碼，屬確定性檢查。
- **為何 live 設非阻斷**：對外連線正式站，Cloudflare / 地區限制可能對 CI 的 datacenter IP
  有不同行為；故僅作資訊性訊號，不讓正式站的外部因素弄紅整條 pipeline。需要時可移除
  `continue-on-error: true` 改為強制阻斷。

## 後續可擴充方向

- 反向測試參數化（空帳號、空密碼、SQL injection 字串等多組無效輸入）。
- 跨瀏覽器矩陣（Chromium / WebKit）對應跨平台需求。
- 與測試團隊確認**測試環境的驗證碼白名單 / 後門 token**，以便正式站也能端到端驗證條件 4/5
  （屆時 `LoginPage.FALLBACK` 已備妥真實 selector，可直接沿用）。
