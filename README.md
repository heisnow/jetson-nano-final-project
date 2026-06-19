# EcoLens 生活回收與標籤辨識助手

EcoLens 是一個貼近日常生活的 Flask 期末專題。使用者打開網站後，可以直接使用目前裝置的鏡頭：電腦使用前鏡頭，手機可切換前後鏡頭，把寶特瓶、手搖飲杯、外送餐盒、鋁箔包、紙箱或包裝標籤對準鏡頭。系統會先解析照片中的顏色、材質感、反光與邊緣特徵，再搭配 OCR 文字、回收規則資料庫、公開資料查詢與網路搜尋摘要，推測分類與處理方式。

目前版本已完成可落地的網站、資料庫、相機頁面、影像特徵分析、OCR 文字讀取、公開資料查詢、文字規則分析與資料分析。未來可加入圖像分類模型，讓系統更自動地判斷鏡頭畫面中的物品。

## 專題動機

每天都有人站在垃圾桶前猶豫：這個杯子能不能回收？鋁箔包算紙類嗎？外送餐盒太油還能丟回收嗎？EcoLens 希望把環保知識變成人人打開網頁就能使用的小工具，讓回收分類像拍照一樣簡單。

## 組員名單

- 林偲駒
- 邱冠凱
- 黃舒禾
- 方守東

## 功能

- Flask 網站主路由 `/`
- 瀏覽器鏡頭掃描頁 `/scan`
- 手機前後鏡頭切換
- 拍照截圖輔助觀察，截圖只留在瀏覽器端
- 影像特徵分析：從截圖中央區域解析棕色紙板、白色餐盒、白色皺褶紙、金屬反光、透明塑膠感、綠色玻璃感與邊緣密度
- 瀏覽器端 OCR 嘗試讀取包裝文字
- 常見材質快捷按鈕：PET、PP、PVC、紙容器、鋁箔包、鐵鋁罐、電池
- 標籤文字分析 API `/api/analyze`
- 公開資料與網路摘要補強 API `/api/web-lookup`
- 影像特徵查詢 API `/api/visual-lookup`
- 使用者回饋 API `/api/feedback`
- 正確 / 不正確回饋與人工修正分類
- 回收規則資料庫 `/rules`
- 使用與分類分析頁 `/analysis`
- 專題計畫頁 `/plan`
- PostgreSQL / SQLite 自動建表
- Playwright 動態網頁爬蟲 `crawler.py`
- Render 部署設定 `render.yaml`

## 專案架構

```text
.
├── app.py
├── database.py
├── models.py
├── crawler.py
├── sample_scan.py
├── requirements.txt
├── requirements-crawler.txt
├── render.yaml
├── Dockerfile
├── PROJECT_PLAN.md
├── PRESENTATION_OUTLINE.md
└── templates
    ├── base.html
    ├── index.html
    ├── scan.html
    ├── rules.html
    ├── analysis.html
    └── plan.html
```

## 本機執行

### 1. 建立與啟動虛擬環境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安裝網站套件

```powershell
pip install -r requirements.txt
```

### 3. 啟動 Flask

```powershell
python app.py
```

瀏覽器開啟：

```text
http://127.0.0.1:5000/
```

本機沒有設定 `DATABASE_URL` 時，系統會使用 `ecolens.db` SQLite 檔案，方便開發與展示。

## 使用 Docker

```powershell
docker build -t ecolens-flask .
docker run --rm -p 5000:5000 ecolens-flask
```

瀏覽器開啟：

```text
http://127.0.0.1:5000/
```

## 使用 Render PostgreSQL

1. 在 Render 建立 PostgreSQL。
2. 複製資料庫的 `Internal Database URL` 或 `External Database URL`。
3. 在 Render Web Service 的 Environment Variables 新增：

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

程式會自動把 Render 的 PostgreSQL URL 轉成 SQLAlchemy 可用格式。

## 部署到 Render

Render Web Service 設定：

```text
Language: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

本專案也提供 `render.yaml`，可使用 Render Blueprint 建立 Web Service 與 PostgreSQL。

## 執行動態網頁爬蟲

爬蟲使用 Playwright，會用瀏覽器載入動態網頁，再把回收相關資訊寫進資料庫。

### 1. 安裝爬蟲套件

```powershell
pip install -r requirements-crawler.txt
python -m playwright install chromium
```

### 2. 測試解析結果

```powershell
python crawler.py --dry-run
```

### 3. 寫入資料庫

```powershell
python crawler.py
```

若要寫入 Render PostgreSQL，請先設定環境變數：

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
python crawler.py
```

## 鏡頭與 AI 擴充

現在版本使用瀏覽器 `getUserMedia` 開啟鏡頭，不需要外接攝像頭或指定型號。後續可以加入：

- OCR：讀取包裝上的 PET、PP、PVC、紙容器等文字。
- 公開資料查詢：優先查詢臺北市資料大平臺「臺北市資源回收分類方式」，找不到時再用搜尋摘要備援。
- 影像特徵分析：目前先從照片中央區域抓取顏色與材質線索，例如棕色紙板、白色餐盒、白色皺褶紙、金屬灰階反光、透明塑膠感、綠色玻璃感與邊緣密度，再把特徵轉成「紙箱、瓦楞紙、衛生紙、紙巾、鐵鋁罐、紙餐盒、保麗龍、寶特瓶、玻璃瓶」等查詢詞。
- 圖像分類模型：未來可改用 TensorFlow Lite、YOLO 或雲端視覺模型，提升無文字物品的辨識穩定度。
- 使用者回饋：讓使用者修正結果，累積成訓練資料，目前已實作正確 / 不正確回饋流程。

## 本次分類依據來源

- 環境部一般廢棄物回收項目與排出方式
- 臺北市資料大平臺「臺北市資源回收分類方式」
- 地方環保局資源回收分類表與宣導資料

## 建議小組分工

- 林偲駒：Flask routes、Jinja templates、網站整合
- 邱冠凱：PostgreSQL schema、Render 設定、部署測試
- 黃舒禾：Playwright crawler、回收規則資料清理
- 方守東：資料分析、鏡頭互動頁、簡報與影片腳本

## 報告繳交提醒

- GitHub repo 連結
- Render 網站公開連結
- 1080p MP4 影片
- 動機與問題說明
- 程式碼講解
- 鏡頭功能、資料庫、爬蟲、資料分析、部署流程展示
- 心得與未來落地想像
