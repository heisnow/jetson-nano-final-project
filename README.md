# Jetson AI 智慧安全帽偵測系統

這是一個使用 Flask 製作的最小可行產品（MVP）。目前已完成主路由 `/`，瀏覽器進入首頁後會顯示小組期末專題主題、專題介紹、預計爬取資料、資料來源網站，以及資料未來如何呈現在網頁上。

## 專題名稱

Jetson AI 智慧安全帽偵測系統

## 組員名單

- 林偲駒
- 邱冠凱
- 黃舒禾

## 專題介紹

本專題使用 NVIDIA Jetson Orin Nano 串接攝影機，透過 YOLO 與 OpenCV 即時偵測人員是否正確配戴安全帽。若偵測到未配戴安全帽的人員，系統會發出警示，並將違規紀錄與相關安全資訊整理後顯示在網站上，可應用於工地、工廠、實驗室等需要安全管理的場域。

## 使用設備

- NVIDIA Jetson Orin Nano
- USB Camera 或 CSI Camera
- LED 警示燈
- 蜂鳴器

## 使用技術

- Python
- OpenCV
- YOLO
- Flask
- Git / GitHub
- PostgreSQL
- Render

## 期末專題規劃

### 可以爬取哪些資料

- 工安案例標題
- 發布日期
- 案例或新聞摘要
- 資料來源連結
- 安全帽偵測違規紀錄

### 資料來源網站

- 勞動部職業安全衛生署公開資訊：職業安全、工安宣導或職災案例等公開資料。
- 工安新聞或公開案例網站：安全帽、工地安全與職災預防相關新聞標題、日期與連結。

正式實作爬蟲前，應先確認來源網站的 robots.txt 與使用條款，並控制請求頻率，避免造成網站負擔。

### 爬取資料如何呈現在網頁上

後續版本會將爬蟲資料存入 PostgreSQL，並在 Flask 網站中以列表或卡片方式呈現。每筆資料預計顯示標題、日期、摘要、來源連結與分類，也會加入 Jetson 安全帽偵測紀錄，讓使用者可以查看違規時間、狀態與相關安全資訊。

## 環境需求

### Docker 方式

- Docker Desktop

### venv 方式

- Python 3.10 以上
- venv
- pip

## 專案啟動方式

本專案建議使用 Docker 啟動，較容易在不同電腦上重現環境。若電腦沒有 Docker，也可以使用 venv。

## 部署到 Render

若希望不同地方的同學都能開啟網站，可以將專案部署到 Render。部署完成後，Render 會提供一個公開網址，例如 `https://your-service-name.onrender.com`。

### 1. 上傳到 GitHub

請先確認專案已經推送到 GitHub repository。

常用指令如下：

```powershell
git add .
git commit -m "Add Flask MVP for Render deployment"
git push
```

### 2. 在 Render 建立 Web Service

1. 登入 Render。
2. 點選 `New`。
3. 選擇 `Web Service`。
4. 連接你的 GitHub repository。
5. 選擇本專案所在的 repository 與 branch。

### 3. Render 設定

若 Render 沒有自動讀取 `render.yaml`，請手動填入以下設定：

```text
Language: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

### 4. 完成部署

按下部署後，等待 Render build 完成。成功後，Render 會產生公開網址，其他同學在不同網路也能直接開啟該網址。

## 使用 Docker 啟動

### 1. 啟動 Docker Desktop

請先打開 Docker Desktop，等到 Docker Desktop 顯示 Docker Engine 已成功啟動後，再執行以下指令。

### 2. 建立 Docker image

請先進入專案資料夾：

```powershell
cd "C:\Users\heisnow\OneDrive\桌面\jetson-nano-finalprojec"
```

建立 image：

```powershell
docker build -t jetson-flask-mvp .
```

### 3. 啟動 container

```powershell
docker run --name jetson-flask-mvp-container -p 5000:5000 jetson-flask-mvp
```

啟動成功後，終端機會顯示類似以下訊息：

```text
Running on http://127.0.0.1:5000
Running on http://172.x.x.x:5000
```

請用瀏覽器開啟：

```text
http://127.0.0.1:5000/
```

### 4. 停止 container

若要停止執行中的 container，可以按 `Ctrl + C`。

如果 container 在背景執行，可使用：

```powershell
docker stop jetson-flask-mvp-container
docker rm jetson-flask-mvp-container
```

## 使用 venv 啟動

### 1. 建立虛擬環境

Windows PowerShell：

```powershell
python -m venv .venv
```

macOS / Linux：

```bash
python3 -m venv .venv
```

### 2. 啟動虛擬環境

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
source .venv/bin/activate
```

啟動成功後，命令列前方通常會出現 `(.venv)`。

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

### 4. 執行 Flask 專案

```bash
python app.py
```

啟動成功後，終端機會顯示類似以下訊息：

```text
Running on http://127.0.0.1:5000
```

請用瀏覽器開啟：

```text
http://127.0.0.1:5000/
```

## 作業截圖建議

1. 瀏覽器開啟 `http://127.0.0.1:5000/`，確認首頁成功顯示「Jetson AI 智慧安全帽偵測系統」。
2. 若使用 Docker，截圖終端機顯示 `docker run` 後 Flask 成功啟動的畫面。
3. 若使用 venv，截圖終端機顯示虛擬環境已啟動，例如命令列前方出現 `(.venv)`。

## 專案結構

```text
.
├── app.py
├── Dockerfile
├── render.yaml
├── requirements.txt
├── README.md
└── templates
    └── index.html
```
