import gspread
from google.oauth2.service_account import Credentials

# 認証情報ファイル名
SERVICE_ACCOUNT_FILE = 'sorakokorohomework-14b559b7fbc5.json'

# スコープ設定
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 認証とクライアント作成
def get_gspread_client():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return gspread.authorize(creds)

if __name__ == "__main__":
    gc = get_gspread_client()
    # アクセスできるスプレッドシート一覧を取得
    sheets = gc.openall()
    print("=== アクセス可能なスプレッドシート一覧 ===")
    for sheet in sheets:
        print(sheet.title) 