import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Sales Dashboard Pro Max", layout="wide")

st.title("📊 รายงานการขาย: Forecast & Analytics")
st.markdown("---")

# --- ส่วน Sidebar: อัปโหลดไฟล์ ---
st.sidebar.header("📂 อัปโหลดไฟล์ข้อมูล")
target_file = st.sidebar.file_uploader("1. อัปโหลดไฟล์เป้าหมาย (Target)", type=['csv', 'xlsx'])
data_file = st.sidebar.file_uploader("2. อัปโหลดไฟล์ยอดขาย (Data)", type=['csv', 'xlsx'])

# ฟังก์ชันทำความสะอาดตัวเลข
def clean_currency(x):
    if isinstance(x, str):
        clean_str = x.replace(',', '').replace(' ', '').strip()
        if clean_str == '-' or clean_str == '':
            return 0.0
        return float(clean_str)
    return x

# --- เริ่มการประมวลผล ---
if target_file and data_file:
    try:
        # 1. โหลดข้อมูล
        if target_file.name.endswith('.csv'):
            df_target = pd.read_csv(target_file)
        else:
            df_target = pd.read_excel(target_file)

        if data_file.name.endswith('.csv'):
            df_data = pd.read_csv(data_file)
        else:
            df_data = pd.read_excel(data_file)

        # 2. Data Cleaning
        # Target
        if pd.isna(df_target.iloc[0]['ชื่อพนักงาน']) or str(df_target.iloc[0]['Total']) == '-':
             df_target = df_target.iloc[1:].copy()
        df_target['Total'] = df_target['Total'].apply(clean_currency)

        # Data
        df_data['Total Price'] = df_data['Total Price'].apply(clean_currency)
        
        # จัดการวันที่ (สำคัญมากสำหรับ Daily & Forecast)
        if 'Doc Date' in df_data.columns:
            # แปลงเป็น datetime (พยายามรองรับหลายรูปแบบ)
            df_data['Doc Date'] = pd.to_datetime(df_data['Doc Date'], dayfirst=True, errors='coerce')
            # สร้างคอลัมน์วันที่แบบไม่มีเวลา
            df_data['DateOnly'] = df_data['Doc Date'].dt.date

        # ==========================================
        # การคำนวณ FORECAST
        # ==========================================
        # หาวันที่ล่าสุดที่มีการขาย
        last_date = df_data['Doc Date'].max()
        days_passed = last_date.day
        
        # หาวันสุดท้ายของเดือนนั้น
        _, num_days_in_month = calendar.monthrange(last_date.year, last_date.month)
        
        total_sales_now = df_data['Total Price'].sum()
        total_target_team = df_target['Total'].sum()
        
        # สูตร Forecast: (ยอดขายปัจจุบัน / วันที่ผ่านมา) * วันทั้งหมดในเดือน
        if days_passed > 0:
            forecast_sales = (total_sales_now / days_passed) * num_days_in_month
        else:
            forecast_sales = 0

        # --- สร้าง Tabs แยกหัวข้อ ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 ภาพรวม & Forecast", 
            "📅 ยอดขายรายวัน (Daily)", 
            "📦 แยกหมวดหมู่ (Category)", 
            "📋 รายละเอียดรายบุคคล"
        ])

        # ==========================================
        # TAB 1: ภาพรวม & Forecast
        # ==========================================
        with tab1:
            st.subheader(f"สรุปยอดเดือน {last_date.strftime('%B %Y')}")
            
            # Metrics 4 ช่อง
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ยอดขายปัจจุบัน", f"{total_sales_now:,.0f} บาท")
            c2.metric("เป้าหมายรวม", f"{total_target_team:,.0f} บาท")
            c3.metric("% ถึงเป้า (Actual)", f"{(total_sales_now/total_target_team*100):.2f}%")
            
            # ช่อง Forecast ใส่สีให้เด่น
            delta_forecast = forecast_sales - total_target_team
            c4.metric("คาดการณ์จบเดือน (Forecast)", f"{forecast_sales:,.0f} บาท", 
                      delta=f"{delta_forecast:,.0f} เทียบเป้า")

            st.markdown("---")
            
            # กราฟเปรียบเทียบรายบุคคล
            st.write("#### 🏆 อันดับยอดขายเทียบเป้า (รายบุคคล)")
            sales_summary = df_data.groupby('Officer (Name)')['Total Price'].sum().reset_index()
            sales_summary.rename(columns={'Total Price': 'Actual Sales'}, inplace=True)
            report = pd.merge(df_target, sales_summary, left_on='ชื่อพนักงาน', right_on='Officer (Name)', how='left')
            report['Actual Sales'] = report['Actual Sales'].fillna(0)
            
            # Sort ตามยอดขาย
            report = report.sort_values(by='Actual Sales', ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=report['ชื่อพนักงาน'], x=report['Total'],
                name='เป้าหมาย (Target)', orientation='h',
                marker=dict(color='rgba(200, 200, 200, 0.5)')
            ))
            fig.add_trace(go.Bar(
                y=report['ชื่อพนักงาน'], x=report['Actual Sales'],
                name='ยอดขายจริง (Actual)', orientation='h',
                marker=dict(color='#28a745'),
                text=report['Actual Sales'], texttemplate='%{text:,.2s}', textposition='inside'
            ))
            fig.update_layout(barmode='overlay', height=600)
            st.plotly_chart(fig, use_container_width=True)

        # ==========================================
        # TAB 2: ยอดขายรายวัน (Daily Trend)
        # ==========================================
        with tab2:
            st.subheader("📅 แนวโน้มยอดขายรายวัน")
            
            daily_sales = df_data.groupby('DateOnly')['Total Price'].sum().reset_index()
            
            fig_daily = px.line(daily_sales, x='DateOnly', y='Total Price', markers=True,
                                title='Daily Sales Performance',
                                labels={'DateOnly': 'วันที่', 'Total Price': 'ยอดขาย (บาท)'})
            fig_daily.update_traces(line_color='#007bff', line_width=3)
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # ตารางข้อมูลรายวัน
            with st.expander("ดูตารางข้อมูลรายวัน"):
                st.dataframe(daily_sales.style.format({'Total Price': '{:,.2f}'}))

        # ==========================================
        # TAB 3: แยกหมวดหมู่ (Category)
        # ==========================================
        with tab3:
            st.subheader("📦 สัดส่วนยอดขายตามหมวดหมู่สินค้า")
            
            # เช็คว่ามีคอลัมน์ Category ไหม
            cat_col = 'Category (Name)' if 'Category (Name)' in df_data.columns else None
            
            if cat_col:
                cat_sales = df_data.groupby(cat_col)['Total Price'].sum().reset_index().sort_values(by='Total Price', ascending=False)
                
                c_chart, c_table = st.columns([2, 1])
                
                with c_chart:
                    fig_cat = px.pie(cat_sales, values='Total Price', names=cat_col, 
                                     hole=0.4, title='Sales Share by Category')
                    st.plotly_chart(fig_cat, use_container_width=True)
                    
                with c_table:
                    st.write("รายละเอียด:")
                    st.dataframe(cat_sales.style.format({'Total Price': '{:,.2f}'}), hide_index=True)
            else:
                st.error("ไม่พบคอลัมน์ 'Category (Name)' ในไฟล์ข้อมูล")

        # ==========================================
        # TAB 4: รายละเอียดรายบุคคล
        # ==========================================
        with tab4:
            st.header("เจาะลึกรายบุคคล")
            staff_list = sorted(df_target['ชื่อพนักงาน'].dropna().unique().tolist())
            selected_staff = st.selectbox("เลือกพนักงาน:", staff_list)

            if selected_staff:
                staff_data = df_data[df_data['Officer (Name)'] == selected_staff].copy()
                
                # แสดง KPI Card ส่วนตัว
                my_total = staff_data['Total Price'].sum()
                my_target_row = report[report['ชื่อพนักงาน'] == selected_staff]
                my_target = my_target_row['Total'].values[0] if not my_target_row.empty else 0
                
                # คำนวณ Forecast ส่วนตัว
                my_forecast = (my_total / days_passed * num_days_in_month) if days_passed > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("ยอดขายจริง", f"{my_total:,.0f}")
                m2.metric("เป้าหมาย", f"{my_target:,.0f}")
                m3.metric("Forecast จบเดือน", f"{my_forecast:,.0f}", delta=f"{my_forecast - my_target:,.0f}")
                
                st.subheader("ประวัติการขาย")
                if not staff_data.empty:
                    show_cols = ['Doc Date', 'Product (Name)', 'Category (Name)', 'Total Price', 'Serial']
                    valid_cols = [c for c in show_cols if c in staff_data.columns]
                    
                    st.dataframe(staff_data[valid_cols].sort_values('Doc Date', ascending=False).style.format({
                        'Total Price': '{:,.2f}',
                        'Doc Date': lambda t: t.strftime('%d/%m/%Y %H:%M')
                    }), use_container_width=True)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

else:
    st.info("👈 กรุณาอัปโหลดไฟล์ Target และ Data เพื่อเริ่มใช้งาน")