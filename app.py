import pytz
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, LocationMessageContent
)
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import traceback
from linebot.v3.messaging.models.get_profile_response import GetProfileResponse

app = Flask(__name__)

# 載入環境變數
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise ValueError("請設定 LINE_CHANNEL_SECRET 和 LINE_CHANNEL_ACCESS_TOKEN 環境變數")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 初始化 Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gs_client = gspread.authorize(credentials)
sheet = gs_client.open("Line打卡記錄表").sheet1

# Webhook 路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    # 🔍 印出 webhook 請求內容以便除錯
    print("📩 收到 webhook 請求：", body)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("❌ Webhook 錯誤：", e)
        traceback.print_exc()
        abort(400)

    return 'OK'

# 接收文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    if event.message.text.strip() == "打卡":
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請傳送您目前的位置📍")]
                )
            )

# 接收位置訊息
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    user_id = event.source.user_id
    address = event.message.address or "未提供"
    latitude = event.message.latitude
    longitude = event.message.longitude
    tz = pytz.timezone('Asia/Taipei')
    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # 動態命名工作表（例如：2025-04）
    month_sheet_name = datetime.now(tz).strftime("%Y-%m")
    try:
        worksheet = gs_client.open("Line打卡記錄表").worksheet(month_sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = gs_client.open("Line打卡記錄表").add_worksheet(title=month_sheet_name, rows="100", cols="5")
        worksheet.append_row(["時間", "使用者名稱", "User ID", "地點", "經緯度"])

    # 取得使用者名稱
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile: GetProfileResponse = line_bot_api.get_profile(user_id)
        display_name = profile.display_name

        # 寫入 Google Sheet 當月分頁
        worksheet.append_row([
            timestamp,
            display_name,
            user_id,
            address,
            f"{latitude}, {longitude}"
        ])

        # 回覆訊息
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"✅ 打卡完成！\n{display_name}\n時間：{timestamp}\n地點：{address}")]
            )
        )
# 本地開發測試用
if __name__ == "__main__":
    app.run(debug=True)
