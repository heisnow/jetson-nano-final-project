# 工安新聞與安全帽風險資料分析平台

這是一個 Flask 期末專題雛形，主題從「綁定特定攝像頭的安全帽辨識」調整為更容易完成與部署的資料產品：先用動態網頁爬蟲收集工安新聞、職災案例與安全帽相關資料，存入 Render PostgreSQL，再用 Flask 網站呈現資料列表與分析結果。NVIDIA Jetson Orin Nano + 攝像頭保留為加分擴充模組，不需要先確定攝像頭型號。

## 專題動機

工地安全不是只有法規與口號，也關係到每一位進場工作者是否能平安回家。本專題希望把 AI 當成能力放大器：人負責判斷、溝通與改善，系統負責收集資料、整理趨勢與即時提醒。先從公開資料理解風險，再讓 Jetson 原型成為現場提醒的起點。

## 組員名單

- 林偲駒
- 邱冠凱
- 黃舒禾
- 方守東

## 功能

- Flask 網站主路由 `/`
- 工安資料列表 `/articles`
- 關鍵字與分類搜尋
- 資料分析頁 `/analysis`
- Jetson 擴充說明與事件資料 `/jetson`
- 專題計畫頁 `/plan`
- PostgreSQL / SQLite 自動建表
- Playwright 動態網頁爬蟲 `crawler.py`
- Jetson 偵測事件模擬寫入 `jetson_event.py`
- Render 部署設定 `render.yaml`

## 專案架構

```text
.
├── app.py
├── database.py
├── models.py
├── crawler.py
├── jetson_event.py
├── requirements.txt
├── requirements-crawler.txt
├── render.yaml
├── Dockerfile
├── PROJECT_PLAN.md
├── PRESENTATION_OUTLINE.md
└── templates
    ├── base.html
    ├── index.html
    ├── articles.html
    ├── analysis.html
    ├── jetson.html
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

Local 沒有設定 `DATABASE_URL` 時，系統會使用 `safety_insight.db` SQLite 檔案，方便開發與展示。

## 使用 Docker

```powershell
docker build -t safety-insight-flask .
docker run --rm -p 5000:5000 safety-insight-flask
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

本專案也提供 `render.yaml`，Render Blueprint 可以依設定建立 Web Service 並連接 PostgreSQL。

## 執行動態網頁爬蟲

爬蟲使用 Playwright，會用瀏覽器載入動態網頁，再把資料寫進資料庫。

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

## Jetson Orin Nano 擴充

因為攝像頭型號尚未確定，本專題不把程式寫死在某個攝像頭型號上。未來只要攝像頭能被 OpenCV 讀取，就能接到同一套資料流程。

目前可用模擬事件測試資料庫與網站：

```powershell
python jetson_event.py --location "A區入口" --status "未戴安全帽" --confidence 0.92
```

## 建議小組分工

- 林偲駒：Flask 路由與頁面整合
- 邱冠凱：PostgreSQL 資料表與 Render 部署
- 黃舒禾：Playwright 動態爬蟲與資料清理
- 方守東：資料分析頁、Jetson 擴充與報告整理

## 報告繳交提醒

- GitHub repo 連結
- Render 網站公開連結
- 1080p MP4 影片
- 動機與問題說明
- 程式碼講解
- 爬蟲、資料庫、資料分析、部署流程展示
- 心得與未來落地想像
