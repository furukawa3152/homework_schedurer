import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

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
    st.title('2025年夏休みの宿題かんりアプリ')
    # 本日の日付と残り日数表示
    today = datetime.date.today()
    target = datetime.date(2025, 8, 29)
    days_left = (target - today).days
    st.write(f'きょうは {today.strftime("%Y年%m月%d日")} です。')
    st.markdown(f'<h2 style="color:#e17055;">夏休みはあと {days_left}日です</h2>', unsafe_allow_html=True)

    tab_add, tab1, tab2 = st.tabs(["新しい宿題をふやす", "そらの宿題", "こころの宿題"])

    with tab_add:
        with st.form(key='add_form'):
            st.subheader('新しい宿題をふやす')
            child = st.selectbox('なまえ', ['そら', 'こころ'])
            content = st.text_input('おべんきょう')
            deadline = st.date_input('いつまでにやる')
            status = st.selectbox('できたかな？（0〜10）', list(range(11)))
            memo = st.text_input('メモ')
            submitted = st.form_submit_button('ふやす')
            if submitted:
                add_homework(child, content, deadline.strftime('%Y/%m/%d'), status, memo)
                st.session_state["added"] = True
        if st.session_state.get("added"):
            st.success('新しい宿題をふやしました')
            st.session_state["added"] = False

    df = fetch_homework_data()
    if df.empty:
        st.info('データがありません')
    else:
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
                        st.warning('まだの宿題:')
                        st.table(not_done[['宿題内容', '進捗', '期限', 'メモ']])
                    for idx, row in filtered_df.iterrows():
                        cols = st.columns([2, 3, 3, 3, 3, 3, 3])
                        # cols[0]（ID）は表示しない
                        cols[0].write(f"なまえ: {row['子供']}")
                        cols[1].write(f"おべんきょう: {row['宿題内容']}")
                        cols[2].write(f"いつまでにやる: {row['期限']}")
                        new_status = cols[3].selectbox(
                            'できたかな？', list(range(11)), index=int(row['進捗']), key=f"status_{row['ID']}")
                        if cols[4].button('なおす', key=f"update_{row['ID']}"):
                            update_homework_status(row['ID'], new_status)
                            st.session_state["updated_id"] = row['ID']
                        cols[5].write(f"メモ: {row['メモ']}")
                    if st.session_state.get("updated_id"):
                        st.success(f"なおしました！")
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