import json
import logging
import os
import sys
import datetime
import gspread

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# INFOレベル以上のログメッセージを拾うように設定する
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数からMessaging APIのチャネルアクセストークンとチャネルシークレットを取得する
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')


# それぞれ環境変数に登録されていないとエラー
if CHANNEL_ACCESS_TOKEN is None:
    logger.error(
        'LINE_CHANNEL_ACCESS_TOKEN is not defined as environmental variables.')
    sys.exit(1)
if CHANNEL_SECRET is None:
    logger.error(
        'LINE_CHANNEL_SECRET is not defined as environmental variables.')
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
webhook_handler = WebhookHandler(CHANNEL_SECRET)


@webhook_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 応答トークンを使って回答を応答メッセージで送る

    GSPREAD_SERVICE_ACCOUNT = os.getenv('GSPREAD_SERVICE_ACCOUNT')
    GSPREAD_SERVICE_ACCOUNT_DICT = json.loads(GSPREAD_SERVICE_ACCOUNT)
    gc = gspread.service_account_from_dict(GSPREAD_SERVICE_ACCOUNT_DICT)
    
    nowdatetime = datetime.datetime.now()
    date = nowdatetime.day
    month = nowdatetime.month
    
    GSPREAD_URL = os.getenv('GSPREAD_URL')
    sh = gc.open_by_url(GSPREAD_URL)

    worksheet = sh.worksheet(f'{month}月')
        
    today_morning_value = str(worksheet.cell(date+1, 2)).split()[2]
    today_lunch_value = str(worksheet.cell(date+1, 3)).split()[2]
    today_dinner_value = str(worksheet.cell(date+1, 4)).split()[2]
    today_midnight_value = str(worksheet.cell(date+1, 5)).split()[2]

    if 'None' in today_morning_value:
        row = 2
    elif 'None' in today_lunch_value:
        row = 3
    elif 'None' in today_dinner_value:
        row = 4
    elif 'None' in today_midnight_value:
        row = 5
    elif 'None' not in today_midnight_value:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='入力済み'))
    else:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='入力エラー'))


    messageText = event.message.text
    try:
        int(messageText)
        worksheet.update_cell(date+1, row, messageText)
        worksheet.update_cell(4, 7, date)
            
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='OK')
        )
        
    except:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text='not int'))
        

def lambda_handler(event, context):

    # リクエストヘッダーにx-line-signatureがあることを確認
    if 'x-line-signature' in event['headers']:
        signature = event['headers']['x-line-signature']

    body = event['body']
    # 受け取ったWebhookのJSONを目視確認できるようにINFOでログに吐く
    logger.info(body)

    try:
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名を検証した結果、飛んできたのがLINEプラットフォームからのWebhookでなければ400を返す
        return {
            'statusCode': 400,
            'body': json.dumps('Only webhooks from the LINE Platform will be accepted.')
        }
    except LineBotApiError as e:
        # 応答メッセージを送ろうとしたがLINEプラットフォームからエラーが返ってきたらエラーを吐く
        logger.error('Got exception from LINE Messaging API: %s\n' % e.message)
        for m in e.error.details:
            logger.error('  %s: %s' % (m.property, m.message))

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
