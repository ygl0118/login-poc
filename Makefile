# SWAG 登入自動化測試 — 快速執行入口
#
# 用法：
#   make setup       建立 .venv 並安裝相依（含 Playwright Chromium）
#   make test        確定性 mock 測試（預設、CI 友善）：前段登入行為 + 條件4 + 條件5
#   make test-mock   同 make test（明確別名）
#   make test-live   真實站 swag.live 測試（-m live）：前段登入行為(條件1/2/3) + 反向
#   make test-all    mock + live 全部執行
#   make clean       移除 .venv 與快取
#   make re          清掉重建後再跑 mock 測試
#
# 可覆寫直譯器：make PYTHON=python3.13 setup
# 需求：Python >= 3.12（Makefile 會檢查）

PYTHON ?= python3.12
VENV   := .venv
BIN    := $(VENV)/bin
PY     := $(BIN)/python
STAMP  := $(VENV)/.installed

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "可用目標："
	@echo "  make setup       建立 .venv 並安裝相依（含 Playwright Chromium）"
	@echo "  make test        mock 測試（確定性、CI 友善）：前段登入行為 + 條件4 + 條件5"
	@echo "  make test-mock   同 make test（明確別名）"
	@echo "  make test-live   真實站 swag.live 測試（-m live）：前段登入行為(條件1/2/3) + 反向"
	@echo "  make test-all    mock + live 全部執行"
	@echo "  make clean       移除 .venv 與快取"
	@echo "  make re          清掉重建後再跑 mock 測試"
	@echo "  （可用 make PYTHON=python3.13 ... 指定直譯器；需 >= 3.12）"

# --- Python 版本檢查（>= 3.12）---
.PHONY: check-python
check-python:
	@command -v $(PYTHON) >/dev/null 2>&1 || { \
		echo "錯誤：找不到 '$(PYTHON)'。請安裝 Python >= 3.12，或以 make PYTHON=<直譯器> 指定。"; exit 1; }
	@$(PYTHON) -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 12) else 1)' || { \
		echo "錯誤：需要 Python >= 3.12，但 $(PYTHON) 為 $$($(PYTHON) -V 2>&1)。"; exit 1; }
	@echo "使用 $$($(PYTHON) -V 2>&1)"

# --- 建立 venv 並安裝相依（以 stamp 檔避免重複安裝）---
$(STAMP): requirements.txt | check-python
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	$(PY) -m playwright install chromium
	@touch $(STAMP)

.PHONY: setup
setup: $(STAMP)
	@echo "環境就緒：$$($(PY) -V 2>&1)"

# --- 測試 ---
.PHONY: test
test: $(STAMP)
	$(PY) -m pytest

.PHONY: test-mock
test-mock: test

.PHONY: test-live
test-live: $(STAMP)
	$(PY) -m pytest tests/test_login.py -m live

.PHONY: test-all
test-all: $(STAMP)
	$(PY) -m pytest -m "live or not live"

# --- 清理 / 重建 ---
.PHONY: clean
clean:
	rm -rf $(VENV) .pytest_cache test-results
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: re
re: clean test
