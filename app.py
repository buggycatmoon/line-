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
