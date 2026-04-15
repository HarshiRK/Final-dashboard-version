import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Advanced Financial Dashboard", layout="wide")

# --- CLEAN FUNCTION ---
def clean_to_float(v):
    if pd.isna(v) or str(v).strip() == "":
        return 0.0
    
    s = str(v).upper().strip()
    is_credit = any(x in s for x in ["CR", "-", "("])
    
    s = re.sub(r'[^0-9.]', '', s)
    
    try:
        if s.count('.') > 1:
            parts = s.split('.')
            s = "".join(parts[:-1]) + "." + parts[-1]
        val = float(s) if s else 0.0
        return -val if is_credit else val
    except:
        return 0.0


# --- PARSER ---
def universal_parser(file):
    df = pd.read_csv(file, header=None)

    header_idx = None
    for i, row in df.iterrows():
        if any("particular" in str(x).lower() for x in row.values):
            header_idx = i
            break

    if header_idx is None:
        return None, "Header not found"

    header_row = df.iloc[header_idx]
    data_rows = df.iloc[header_idx + 1:]

    account_cols = [i for i, v in enumerate(header_row) if "particular" in str(v).lower()]

    all_data = []
    month_keywords = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec","202"]

    for i, val in enumerate(header_row):
        if "closing" in str(val).lower():

            # find account column
            acc_col = None
            for ac in reversed(account_cols):
                if ac < i:
                    acc_col = ac
                    break

            if acc_col is None:
                continue

            # find month
            month = "Total"
            for r in range(header_idx):
                for c in range(i, acc_col - 1, -1):
                    cell = str(df.iloc[r, c]).lower()
                    if any(m in cell for m in month_keywords):
                        month = df.iloc[r, c]
                        break

            temp = pd.DataFrame()
            temp['Account'] = data_rows.iloc[:, acc_col].astype(str).str.strip()
            temp = temp[~temp['Account'].str.match(r'^[0-9.\sDrCr()-]+$', na=False)]

            temp['Amount'] = data_rows.iloc[:, i].apply(clean_to_float)
            temp['Month'] = month

            all_data.append(temp)

    if not all_data:
        return None, "No Closing Balance found"

    return pd.concat(all_data).reset_index(drop=True), None


# --- UI ---
st.title("📊 Advanced Financial Dashboard")
st.markdown("Now with Profit/Loss & Trends 🚀")

uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")

if uploaded:
    data, err = universal_parser(uploaded)

    if err:
        st.error(err)

    else:
        # --- CATEGORY ---
        def quick_cat(x):
            x = str(x).lower()

            if any(i in x for i in ['cash','bank','inventory','asset','receivable']):
                return 'Assets'
            if any(i in x for i in ['loan','payable','capital','equity','reserve']):
                return 'Liabilities'
            if any(i in x for i in ['sale','revenue','income']):
                return 'Revenue'
            if any(i in x for i in ['purchase','expense','rent','salary']):
                return 'Expenses'
            return 'Others'

        data['Category'] = data['Account'].apply(quick_cat)

        # --- MONTH SELECT ---
        months = list(data['Month'].unique())
        sel_month = st.sidebar.selectbox("Select Month", months)
        view = data[data['Month'] == sel_month]
        # --- PREVIOUS MONTH DATA ---
month_order = list(data['Month'].unique())

try:
    current_index = month_order.index(sel_month)
    prev_month = month_order[current_index - 1]
    prev_view = data[data['Month'] == prev_month]
except:
    prev_view = pd.DataFrame()

        # --- METRICS ---
        assets = view[view['Category'] == 'Assets']['Amount'].sum()
        liab = view[view['Category'] == 'Liabilities']['Amount'].sum()
        revenue = view[view['Category'] == 'Revenue']['Amount'].sum()
        expenses = view[view['Category'] == 'Expenses']['Amount'].sum()

        profit = revenue - abs(expenses)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Assets", f"₹{abs(assets):,.0f}")
        c2.metric("Liabilities", f"₹{abs(liab):,.0f}")
        c3.metric("Revenue", f"₹{abs(revenue):,.0f}")
        c4.metric("Profit/Loss", f"₹{profit:,.0f}", delta="Profit" if profit>=0 else "Loss")

        st.divider()
# --- VARIANCE ANALYSIS ---
st.subheader("📊 Variance Analysis")

current_summary = view.groupby('Category')['Amount'].sum()
prev_summary = prev_view.groupby('Category')['Amount'].sum()

variance_df = pd.DataFrame({
    'Current': current_summary,
    'Previous': prev_summary
}).fillna(0)

variance_df['Change'] = variance_df['Current'] - variance_df['Previous']

variance_df['% Change'] = variance_df.apply(
    lambda x: (x['Change'] / x['Previous'] * 100) if x['Previous'] != 0 else 0,
    axis=1
)

st.dataframe(
    variance_df.style.format({
        'Current': '₹{:,.0f}',
        'Previous': '₹{:,.0f}',
        'Change': '₹{:,.0f}',
        '% Change': '{:.1f}%'
    }),
    use_container_width=True
)

        # --- CHARTS ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Category Breakdown")
            fig = px.pie(view, values=view['Amount'].abs(), names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Monthly Trend")
            trend = data.groupby('Month')['Amount'].sum().reset_index()
            fig2 = px.line(trend, x='Month', y='Amount', markers=True)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("Detailed Table")
        st.dataframe(view[['Account','Category','Amount']], use_container_width=True)
