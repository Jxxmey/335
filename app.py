import streamlit as st
import pandas as pd
import plotly.express as px

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Sales Dashboard", layout="wide")

st.title("📊 แดชบอร์ดรายงานการขายรายบุคคล")
st.markdown("---")

# --- ส่วน Sidebar: ตั้งค่า Target ---
st.sidebar.header("1. ข้อมูลเป้าหมาย (Target)")
# ทางเลือก 1: ใส่ลิงก์ Google Sheets (CSV)
target_url = st.sidebar.text_input("วางลิงก์ Google Sheets (CSV) ที่นี่:", help="ลิงก์จากเมนู File > Share > Publish to web > เลือกเป็น CSV")

# ทางเลือก 2: อัปโหลดไฟล์ Target (กรณีไม่ได้ใช้ Google Sheets)
target_file = st.sidebar.file_uploader("หรืออัปโหลดไฟล์ Target (Excel/CSV)", type=['xlsx', 'csv'])

# --- ส่วน Main: อัปโหลด Data ---
st.header("2. อัปโหลดข้อมูลดิบ (Raw Data)")
uploaded_file = st.file_uploader("ลากไฟล์ Data (Excel/CSV) มาวางที่นี่", type=['xlsx', 'csv'])

# --- ฟังก์ชันทำความสะอาดตัวเลข (ลบลูกน้ำ) ---
def clean_currency(x):
    if isinstance(x, str):
        return float(x.replace(',', '').replace(' ', ''))
    return x

# --- เริ่มการประมวลผล ---
if uploaded_file is not None:
    try:
        # 1. โหลดข้อมูล Raw Data
        if uploaded_file.name.endswith('.csv'):
            df_data = pd.read_csv(uploaded_file)
        else:
            df_data = pd.read_excel(uploaded_file)

        # 2. โหลดข้อมูล Target
        df_target = None
        if target_url:
            df_target = pd.read_csv(target_url)
        elif target_file:
            if target_file.name.endswith('.csv'):
                df_target = pd.read_csv(target_file)
            else:
                df_target = pd.read_excel(target_file)
        
        if df_target is None:
            st.warning("⚠️ กรุณาใส่ลิงก์ Google Sheets หรืออัปโหลดไฟล์ Target ก่อน")
        else:
            # --- Data Processing ---
            # ปรับชื่อคอลัมน์ให้ตรงกัน (แก้ไขชื่อตามไฟล์จริงของคุณได้ที่นี่)
            # สมมติ Data ใช้ 'Officer (Name)' และ Target ใช้ 'ชื่อพนักงาน'
            
            # แปลงตัวเลข (ลบลูกน้ำ)
            col_sales_data = 'Total Price' # ชื่อคอลัมน์ยอดขายใน Data
            col_staff_data = 'Officer (Name)' # ชื่อคอลัมน์พนักงานใน Data
            
            col_target_target = 'Total' # ชื่อคอลัมน์เป้าใน Target
            col_staff_target = 'ชื่อพนักงาน' # ชื่อคอลัมน์พนักงานใน Target

            # Clean Data
            df_data[col_sales_data] = df_data[col_sales_data].apply(clean_currency)
            df_target[col_target_target] = df_target[col_target_target].apply(clean_currency)

            # รวมยอดขายตามพนักงาน
            sales_summary = df_data.groupby(col_staff_data)[col_sales_data].sum().reset_index()
            sales_summary.rename(columns={col_sales_data: 'Actual Sales'}, inplace=True)

            # เชื่อมกับ Target
            report = pd.merge(sales_summary, df_target[[col_staff_target, col_target_target]], 
                              left_on=col_staff_data, right_on=col_staff_target, how='left')
            
            report.rename(columns={col_target_target: 'Target Sales'}, inplace=True)
            
            # คำนวณ %
            report['% Achieved'] = (report['Actual Sales'] / report['Target Sales']) * 100
            report['% Achieved'] = report['% Achieved'].fillna(0).round(2)

            # --- แสดงผล Dashboard ---
            
            # 1. ภาพรวม (Metrics)
            total_sales = report['Actual Sales'].sum()
            total_target = report['Target Sales'].sum()
            total_achieved = (total_sales / total_target * 100) if total_target > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("ยอดขายรวมทั้งหมด", f"{total_sales:,.0f} บาท")
            c2.metric("เป้าหมายรวม", f"{total_target:,.0f} บาท")
            c3.metric("% ความสำเร็จรวม", f"{total_achieved:.2f}%", delta_color="normal")

            st.markdown("---")

            # 2. กราฟแท่ง (Bar Chart)
            st.subheader("📈 เทียบยอดขาย vs เป้าหมาย รายบุคคล")
            
            # จัดเตรียมข้อมูลสำหรับกราฟ (Melt data เพื่อให้พล็อตกราฟคู่ได้ง่าย)
            chart_data = report[[col_staff_data, 'Actual Sales', 'Target Sales']].melt(id_vars=col_staff_data, var_name='Type', value_name='Amount')
            
            fig = px.bar(chart_data, x=col_staff_data, y='Amount', color='Type', 
                         barmode='group', text_auto='.2s',
                         color_discrete_map={'Actual Sales': '#28a745', 'Target Sales': '#ffc107'})
            st.plotly_chart(fig, use_container_width=True)

            # 3. ตารางรายละเอียด (Table)
            st.subheader("📋 รายละเอียดรายบุคคล")
            st.dataframe(report.style.format({
                "Actual Sales": "{:,.2f}", 
                "Target Sales": "{:,.2f}", 
                "% Achieved": "{:.2f}%"
            }))

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        st.info("คำแนะนำ: ตรวจสอบว่าชื่อคอลัมน์ในไฟล์ตรงกับในโค้ดหรือไม่ (Total Price, Officer (Name), etc.)")