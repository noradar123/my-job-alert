"""
job-alert-bot: 監控指定公司頁面(career/events page)的內容變化,一有變化就用 Telegram 通知。

運作邏輯:
1. 讀取 config.yaml 裡的目標清單
2. 對每個網址抓取內容,清掉 script/style 等雜訊後取得純文字
3. 算出這段文字的 hash,跟上次存的 state.json 比對
4. 如果 hash 不同 -> 代表頁面內容變了 -> 發 Telegram 通知 + 更新 state.json
5. state.json 會被 GitHub Actions commit 回 repo,下次執行才知道"上次"長怎樣
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("targets", [])


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_text(url: str, selector: str | None) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 拿掉不影響「實質內容」的雜訊標籤
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    node = soup.select_one(selector) if selector else soup.body
    if node is None:
        node = soup

    text = node.get_text(separator=" ", strip=True)
    # 把多餘空白壓縮,避免格式微調被誤判成「內容改變」
    text = " ".join(text.split())
    return text


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[warn] 沒有設定 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID,只印在 log 裡:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[error] Telegram 發送失敗: {e}")


def main():
    targets = load_config()
    state = load_state()
    changed_any = False

    for t in targets:
        name = t["name"]
        url = t["url"]
        selector = t.get("selector")

        try:
            text = fetch_text(url, selector)
        except Exception as e:
            print(f"[skip] {name} 抓取失敗: {e}")
            continue

        new_hash = content_hash(text)
        old_hash = state.get(url, {}).get("hash")

        if old_hash is None:
            # 第一次看到這個網址,先記錄基準值,不發通知(避免第一次跑就狂發)
            print(f"[init] {name}: 建立初始快照")
        elif old_hash != new_hash:
            changed_any = True
            msg = (
                f"🔔 {name} 的頁面內容有更新!\n"
                f"{url}\n"
                f"(可能是新活動 / 開放報名 / 職缺更新,建議去看看)"
            )
            print(f"[changed] {name}")
            send_telegram(msg)
        else:
            print(f"[same] {name}: 沒有變化")

        state[url] = {
            "name": name,
            "hash": new_hash,
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 對同一台主機的請求之間留點間隔,別打太快
        time.sleep(2)

    save_state(state)

    if changed_any:
        print("本次執行偵測到至少一個變化。")
    else:
        print("本次執行沒有偵測到變化。")


if __name__ == "__main__":
    main()
