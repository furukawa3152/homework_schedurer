import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 認証情報の取得（ローカル: jsonファイル, Cloud: st.secrets）
def get_service_account_info():
    try:
        # secrets.tomlが存在し、Cloud/ローカル問わずst.secretsが使える場合
        service_account_info = st.secrets["google_service_account"]
        return service_account_info, None
    except Exception:
        # secrets.tomlがない場合はローカル用jsonファイル
        json_path = 'sorakokorohomework-14b559b7fbc5.json'
        return None, json_path

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_NAME = 'sorakokoro2025'

# gspreadクライアント取得
def get_gspread_client():
    service_account_info, json_path = get_service_account_info()
    if service_account_info:
        creds = Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
    else:
        creds = Credentials.from_service_account_file(
            json_path, scopes=SCOPES
        )
    return gspread.authorize(creds)

def get_worksheet():
    gc = get_gspread_client()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.sheet1  # 1枚目のシートを使用
    return worksheet

def fetch_homework_data():
    ws = get_worksheet()
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df

def add_homework(child, content, deadline, status, memo):
    ws = get_worksheet()
    # 既存データ取得
    data = ws.get_all_records()
    if data:
        max_id = max([row['ID'] for row in data])
    else:
        max_id = 0
    new_id = max_id + 1
    ws.append_row([new_id, child, content, deadline, status, memo])

# Streamlitアプリ本体
def main():
    st.title('宿題進捗管理アプリ')
    st.write('Googleスプレッドシートと連携しています')

    # --- 宿題追加フォーム ---
    with st.form(key='add_form'):
        st.subheader('宿題を追加')
        child = st.selectbox('子供', ['そら', 'こころ'])
        content = st.text_input('宿題内容')
        deadline = st.date_input('期限')
        status = st.selectbox('進捗（0〜10）', list(range(11)))
        memo = st.text_input('メモ')
        submitted = st.form_submit_button('追加')
        if submitted:
            add_homework(child, content, deadline.strftime('%Y/%m/%d'), status, memo)
            st.session_state["added"] = True

    if st.session_state.get("added"):
        st.success('宿題を追加しました')
        st.session_state["added"] = False

    df = fetch_homework_data()
    if df.empty:
        st.info('データがありません')
    else:
        tab1, tab2 = st.tabs(["そらの宿題", "こころの宿題"])
        for tab, name in zip([tab1, tab2], ["そら", "こころ"]):
            with tab:
                st.subheader(f'{name}の宿題リスト')
                filtered_df = df[df['子供'] == name]
                if filtered_df.empty:
                    st.info('データがありません')
                else:
                    # 達成率グラフ
                    total = len(filtered_df)
                    if total > 0:
                        progress_sum = filtered_df['進捗'].astype(int).sum()
                        percent = int(progress_sum / (total * 10) * 100)
                        st.progress(percent, text=f"達成率: {percent}%")
                        # 宿題ごとの進捗棒グラフ
                        st.bar_chart(filtered_df.set_index('宿題内容')['進捗'])
                    # 未達成宿題リスト
                    not_done = filtered_df[filtered_df['進捗'].astype(int) < 10]
                    if not not_done.empty:
                        st.warning('あとやるべき宿題:')
                        st.table(not_done[['宿題内容', '進捗', '期限']])
                    for idx, row in filtered_df.iterrows():
                        cols = st.columns([2, 3, 3, 3, 3, 3])
                        cols[0].write(f"ID: {row['ID']}")
                        cols[1].write(f"子供: {row['子供']}")
                        cols[2].write(f"内容: {row['宿題内容']}")
                        cols[3].write(f"期限: {row['期限']}")
                        new_status = cols[4].selectbox(
                            '進捗', list(range(11)), index=int(row['進捗']), key=f"status_{row['ID']}")
                        if cols[5].button('更新', key=f"update_{row['ID']}"):
                            update_homework_status(row['ID'], new_status)
                            st.session_state["updated_id"] = row['ID']
                    if st.session_state.get("updated_id"):
                        st.success(f"ID {st.session_state['updated_id']} の進捗を更新しました")
                        st.session_state["updated_id"] = None

# 進捗更新用関数
def update_homework_status(target_id, new_status):
    ws = get_worksheet()
    data = ws.get_all_records()
    for i, row in enumerate(data):
        if row['ID'] == target_id:
            ws.update_cell(i+2, 5, new_status)  # 進捗カラムを数字で更新
            break

if __name__ == "__main__":
    main() 