import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import altair as alt

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
                        st.progress(percent, text=f"がんばりメーター: {percent}%")
                        # 宿題ごとの進捗棒グラフ（Y軸0〜10固定）
                        # 進捗に応じて色分け用のデータを作成
                        chart_df = filtered_df.copy()
                        chart_df['進捗レベル'] = chart_df['進捗'].apply(
                            lambda x: 'よくできている' if x >= 8 else ('がんばっている' if x >= 4 else 'まだこれから')
                        )
                        
                        chart = alt.Chart(chart_df).mark_bar().encode(
                            x='宿題内容',
                            y=alt.Y('進捗', scale=alt.Scale(domain=[0, 10], nice=False), axis=alt.Axis(values=list(range(0, 11)))),
                            color=alt.Color('進捗レベル', scale=alt.Scale(
                                domain=['まだこれから', 'がんばっている', 'よくできている'],
                                range=['red', 'orange', 'green']
                            )),
                            tooltip=['宿題内容', '進捗']
                        ).properties(
                            title='たっせいじょうきょう',
                            width=400,
                            height=300
                        )
                        st.altair_chart(chart, use_container_width=True)
                    # 未達成宿題リスト
                    not_done = filtered_df[filtered_df['進捗'].astype(int) < 10]
                    if not not_done.empty:
                        st.warning('のこってる宿題:')
                        st.table(not_done[['宿題内容', '進捗', '期限', 'メモ']])
                    for idx, row in filtered_df.iterrows():
                        cols = st.columns([5, 3, 3, 3, 5, 1])
                        cols[0].write(f"{row['宿題内容']}")
                        cols[1].write(f"{row['期限']}　　までに終わる")
                        new_status = cols[2].selectbox(
                            'たっせいりつ', list(range(11)), index=int(row['進捗']), key=f"status_{row['ID']}")
                        if cols[3].button('こうしん', key=f"update_{row['ID']}"):
                            update_homework_status(row['ID'], new_status)
                            st.session_state["updated_id"] = row['ID']
                            st.session_state["needs_rerun"] = True
                        cols[4].write(f"{row['メモ']}")
                    if st.session_state.get("updated_id"):
                        st.success(f"なおしました！")
                        st.session_state["updated_id"] = None
                        if st.session_state.get("needs_rerun"):
                            st.session_state["needs_rerun"] = False
                            st.rerun()

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