import os

from flask import Flask, render_template


app = Flask(__name__)


PROJECT = {
    "name": "Jetson AI 智慧安全帽偵測系統",
    "team_members": ["林偲駒", "邱冠凱", "黃舒禾"],
    "summary": (
        "本專題使用 NVIDIA Jetson Orin Nano 串接攝影機，透過 YOLO 與 OpenCV "
        "即時偵測人員是否正確配戴安全帽。若偵測到未配戴安全帽的人員，"
        "系統會發出警示，並將違規紀錄與相關安全資訊整理後顯示在網站上。"
    ),
    "crawler_sources": [
        {
            "title": "勞動部職業安全衛生署公開資訊",
            "description": "爬取職業安全、工安宣導或職災案例等公開資料。",
        },
        {
            "title": "工安新聞或公開案例網站",
            "description": "整理安全帽、工地安全與職災預防相關新聞標題、日期與連結。",
        },
    ],
    "data_items": [
        "工安案例標題",
        "發布日期",
        "案例或新聞摘要",
        "資料來源連結",
        "安全帽偵測違規紀錄",
    ],
    "display_plan": (
        "網站首頁會顯示專題介紹，後續版本會以列表或卡片呈現爬蟲資料，"
        "並加入安全帽偵測紀錄、時間、狀態與來源連結。"
    ),
    "future_stack": ["PostgreSQL", "Crawler", "Flask", "Render"],
}


@app.route("/")
def index():
    return render_template("index.html", project=PROJECT)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
