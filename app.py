from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhooks import MessageEvent, TextMessageContent, LocationMessageContent
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# 載入環境變數
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise ValueError("請設定 LINE_CHANNEL_SECRET 和 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 初始化 Google Sheets
# 初始化 Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gs_client = gspread.authorize(credentials)
sheet = gs_client.open("Line打卡記錄表").sheet1

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    # 🟡 印出收到的 webhook 原始內容，方便偵錯
    print("📩 收到 webhook 請求：", body)

    try:
        # 嘗試處理 webhook 訊息
        handler.handle(body, signature)
    except Exception as e:
        import traceback
        # ❌ 印出錯誤訊息與堆疊資訊
        print("❌ Webhook 錯誤：", e)
        traceback.print_exc()
        abort(400)

    return 'OK'


from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage  # 別忘記加這行

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    if event.message.text.strip() == "打卡":
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextMessage(text="請傳送您目前的位置📍")
                ]
            )

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    user_id = event.source.user_id
    address = event.message.address or "未提供"
    latitude = event.message.latitude
    longitude = event.message.longitude
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 寫入 Google Sheets
    sheet.append_row([timestamp, user_id, address, latitude, longitude])

    with ApiClient(configuration) as api_client:
       line_bot_api.reply_message(
    event.reply_token,
    [
        TextMessage(text=f"✅ 打卡完成！\n時間：{timestamp}\n地點：{address}")
    ]
)

if __name__ == "__main__":
    app.run(debug=True)
