# job-alert-bot

自動監控指定公司的 career page / events page,一有內容變化就用 Telegram 通知你。

## 運作方式

- `config.yaml` 裡列出你要追蹤的公司與網址
- GitHub Actions 每 6 小時執行一次 `monitor.py`
- script 抓取每個網址的文字內容、算 hash,跟上次記錄的 `state.json` 比對
- 如果內容變了 -> 發 Telegram 訊息給你 -> 更新 `state.json` 並 commit 回 repo

完全免費(GitHub Actions 對 public repo 無限額度,private repo 每月也有免費額度),不用自己開 server。

## 設定步驟

### 1. 建立 Telegram Bot(拿 Token)

1. Telegram 搜尋 `@BotFather`,傳送 `/newbot`
2. 照指示取名字,完成後會拿到一組 `TELEGRAM_BOT_TOKEN`(長得像 `123456789:ABCdefGhIJKlmNoPQRstuVwxyZ`)

### 2. 拿到你的 Chat ID

1. 先傳一則訊息給你剛建立的 bot(隨便打字都可以)
2. 瀏覽器打開:
   `https://api.telegram.org/bot<你的TOKEN>/getUpdates`
3. 回傳的 JSON 裡找 `"chat":{"id": ...}`,那個數字就是 `TELEGRAM_CHAT_ID`

### 3. 建立 GitHub Repo

1. 把這個資料夾裡的所有檔案 push 到一個新的 GitHub repo(public 或 private 都可以)
2. 進入 repo 的 `Settings -> Secrets and variables -> Actions -> New repository secret`,新增兩個 secret:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

### 4. 編輯 `config.yaml`

把你想追蹤的公司名稱、網址填進去。第一次跑的時候只會建立「基準快照」,不會發通知(避免一開始就狂發一堆訊息)——第二次之後如果偵測到變化才會通知你。

### 5. 手動測試一次

進 GitHub repo 的 `Actions` 分頁 -> 選 `Job Alert Monitor` -> `Run workflow`,可以馬上跑一次確認有沒有正常運作,不用等排程。

## 已知限制 & 之後可以加強的地方

- **JS render 的頁面抓不到內容**:有些公司的 career page 是 React/Vue 等前端框架動態渲染的,單純用 `requests` 抓到的 HTML 是空的。如果遇到這種情況,需要把 `requests` 換成 `playwright`(headless browser),我可以之後幫你加上去。
- **假警報**:如果某個頁面有會隨機變動的區塊(輪播圖、"上次更新時間"字樣、隨機推薦內容),可能會一直觸發「內容改變」的通知。這時候可以在 `config.yaml` 用 `selector` 欄位指定只監控頁面的某一個區塊(例如 `#job-listings` 或 `.events-section`),減少雜訊。用瀏覽器 F12 開發者工具找到該區塊的 class/id 即可。
- **需要登入才看得到的頁面**(例如某些學校專屬的 Handshake 頁面):目前的簡單版本沒辦法處理,需要額外的 session/cookie 管理。
- **通知內容比較陽春**:目前只會告訴你「有變化」,沒有告訴你具體改了什麼。之後可以加上文字 diff,把新增的段落摘錄出來一起發送。
