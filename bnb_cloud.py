
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 設定 ---
# 這裡填入你的 Google 試算表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1tBnJ5mR3oJ37GYeEaDBUw7CAdY2VslX3df1OLL7pSc0/edit?usp=sharing"

# --- 頁面設定 ---
st.set_page_config(page_title="民宿收支管家(雲端版)", layout="wide")
st.title("🏡 民宿收支管理系統 (雲端版)")

# --- 連接 Google Sheets ---
# 建立連線物件
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取資料函式 (加上 ttl=0 確保每次都抓到最新資料)
def load_data():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
        # 處理空值與日期格式
        df = df.dropna(how='all') # 刪除全空行
        df['日期'] = pd.to_datetime(df['日期'])
        return df
    except Exception as e:
        st.error(f"連線錯誤，請檢查網址或權限: {e}")
        return pd.DataFrame(columns=['日期', '類型', '項目', '金額', '備註'])

# --- 側邊欄：新增收支 ---
st.sidebar.header("➕ 新增紀錄")

with st.sidebar.form("entry_form", clear_on_submit=True):
    date_input = st.date_input("日期", datetime.today())
    entry_type = st.selectbox(
        "類型", 
        ["收入-訂金", "收入-尾款", "支出-一般 (水電/備品)", "支出-年費 (稅金/保險)"]
    )
    item_input = st.text_input("項目說明")
    amount_input = st.number_input("金額", min_value=0, step=100)
    note_input = st.text_input("備註")
    
    submitted = st.form_submit_button("儲存紀錄")
    
    if submitted:
        # 1. 讀取目前資料
        current_df = load_data()
        
        # 2. 建立新的一筆資料
        new_row = pd.DataFrame([{
            '日期': date_input.strftime('%Y-%m-%d'),
            '類型': entry_type,
            '項目': item_input,
            '金額': amount_input,
            '備註': note_input
        }])
        
        # 3. 合併並寫回 Google Sheets
        updated_df = pd.concat([current_df, new_row], ignore_index=True)
        
        # --- 關鍵修正：先轉成日期格式，再轉成文字格式 ---
        updated_df['日期'] = pd.to_datetime(updated_df['日期']).dt.strftime('%Y-%m-%d')
        
        conn.update(spreadsheet=SPREADSHEET_URL, data=updated_df)
        st.sidebar.success("✅ 已新增至 Google 試算表！")
        
        # 強制重新整理以顯示新資料
        st.rerun()

# --- 主畫面：顯示報表 ---
df = load_data()

if not df.empty:
    # 這裡的邏輯跟單機版一樣，只是資料來源變了
    current_year = datetime.now().year
    # 確保有年份資料
    years = sorted(df['日期'].dt.year.unique(), reverse=True)
    if not years:
        selected_year = current_year
    else:
        selected_year = st.selectbox("選擇年份", options=years)
    
    df_year = df[df['日期'].dt.year == selected_year]
    
    # 計算年費分攤
    annual_fees = df_year[df_year['類型'] == '支出-年費 (稅金/保險)']['金額'].sum()
    monthly_amortized_fee = annual_fees / 12

    st.markdown(f"### 📅 {selected_year} 財務概況")
    col1, col2 = st.columns(2)
    col1.metric("年度總年費", f"${annual_fees:,.0f}")
    col2.metric("月攤提成本", f"${monthly_amortized_fee:,.0f}")
    
    st.divider()

    st.subheader("📊 每月結算")
    months = range(1, 13)
    monthly_report = []

    for month in months:
        mask = (df_year['日期'].dt.month == month)
        df_month = df_year[mask]
        
        income = df_month[df_month['類型'].str.contains('收入')]['金額'].sum()
        expense_general = df_month[df_month['類型'] == '支出-一般 (水電/備品)']['金額'].sum()
        profit = income - expense_general - monthly_amortized_fee
        
        monthly_report.append({
            '月份': f"{month}月",
            '總收入': income,
            '一般支出': expense_general,
            '淨利 (含攤提)': profit
        })

    report_df = pd.DataFrame(monthly_report)
    st.dataframe(
        report_df.style.format("{:,.0f}", subset=['總收入', '一般支出', '淨利 (含攤提)'])
                 .background_gradient(subset=['淨利 (含攤提)'], cmap='RdYlGn'),
        use_container_width=True
    )

    st.subheader("📝 近期紀錄")
    st.dataframe(df.sort_values('日期', ascending=False), use_container_width=True)

else:
    st.info("目前 Google 試算表中沒有資料，請新增第一筆！")
