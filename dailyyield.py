import streamlit as st
import pdfplumber
import pandas as pd

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="SFC Super Dashboard", layout="wide")
st.title("🐔 SFC Super Dashboard: วิเคราะห์ Yield & ราคาบาลานซ์ชิ้นส่วน")

st.info("💡 **ทริคการใช้งาน:** คุณสามารถเลื่อนลงไปใช้ **ส่วนที่ 2 (คำนวณราคา)** ได้ทันทีโดยไม่จำเป็นต้องอัปโหลด PDF ครับ!")

# 2. ฐานข้อมูลเริ่มต้น
if 'part_data' not in st.session_state:
    st.session_state.part_data = pd.DataFrame([
        {"รายการ": "ขนไก่", "% Yield": 7.0, "ราคาตลาด (บ./กก.)": 1.7},
        {"รายการ": "หัวไก่", "% Yield": 2.5, "ราคาตลาด (บ./กก.)": 6.0},
        {"รายการ": "ไส้", "% Yield": 7.0, "ราคาตลาด (บ./กก.)": 6.0},
        {"รายการ": "เลือด", "% Yield": 2.0, "ราคาตลาด (บ./กก.)": 1.0},
        {"รายการ": "โครง", "% Yield": 20.0, "ราคาตลาด (บ./กก.)": 14.0},
        {"รายการ": "เครื่องใน", "% Yield": 5.8, "ราคาตลาด (บ./กก.)": 36.0},
        {"รายการ": "น่องติดสะโพก", "% Yield": 25.0, "ราคาตลาด (บ./กก.)": 65.0},
        {"รายการ": "อกไก่", "% Yield": 22.0, "ราคาตลาด (บ./กก.)": 62.0},
        {"รายการ": "สันใน", "% Yield": 3.5, "ราคาตลาด (บ./กก.)": 70.0},
        {"รายการ": "ขาไก่", "% Yield": 2.5, "ราคาตลาด (บ./กก.)": 40.0},
        {"รายการ": "ปีกเต็ม", "% Yield": 7.8, "ราคาตลาด (บ./กก.)": 76.0}
    ])

if 'm2_locks' not in st.session_state:
    st.session_state.m2_locks = [False] * 11
if 'm2_lock_prices' not in st.session_state:
    st.session_state.m2_lock_prices = st.session_state.part_data["ราคาตลาด (บ./กก.)"].tolist()

# 3. เมนูด้านข้าง
with st.sidebar:
    st.header("⚙️ ตั้งค่าต้นทุนโรงงาน")
    factory_cost = st.number_input("ค่าใช้จ่ายโรงงาน/ค่าเชือด (บาท/กก.)", value=4.08, step=0.01)
    target_live_bird = st.number_input("ราคาไก่เป็นเป้าหมาย (บาท/กก.)", value=43.00, step=0.50)

# ==========================================
# ส่วนที่ 1: ประมวลผลใบแจ้งคิวไก่ (PDF)
# ==========================================
total_live_bird_all = 0
summary_df = pd.DataFrame()

with st.expander("📄 ส่วนที่ 1: อัปโหลดใบแจ้งคิวไก่ PDF (คลิกเพื่อเปิด/ปิด)", expanded=False):
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ใบแจ้งคิวไก่ (PDF)", type="pdf")

    if uploaded_file is not None:
        with st.spinner('กำลังประมวลผล...'):
            try:
                data = []
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            for row in table:
                                row_text = " ".join([str(c) for c in row if c is not None])
                                if any(x in row_text for x in ["Total", "Avg", "Weigh", "เซ็ลดเสร็จ", "ต้นที"]):
                                    continue
                                
                                group_name = "ไม่ระบุ"
                                for cell in row:
                                    if cell is None: continue
                                    text = str(cell).replace("\n", " ").strip()
                                    if "/" in text:
                                        prefix = text.split("/")[0].strip()
                                        if prefix and not prefix[0].isdigit() and "ฟาร์ม" not in prefix:
                                            group_name = prefix
                                            break
                                    else:
                                        text_upper = text.upper()
                                        if text_upper.startswith("DFG"):
                                            group_name = "DFG"
                                            break
                                        elif text_upper.startswith("CP") or text.startswith("ซีพี"):
                                            group_name = "CP"
                                            break
                                        elif text_upper.startswith("SFC") and len(text_upper) > 4: 
                                            group_name = "SFC"
                                            break
                                
                                weight_val = 0
                                for cell in row:
                                    if cell is None: continue
                                    parts = str(cell).replace("\n", " ").split()
                                    for p in parts:
                                        clean_p = p.replace(",", "").strip()
                                        try:
                                            val = float(clean_p)
                                            if val > 500: 
                                                if val > weight_val: weight_val = val
                                        except ValueError: pass
                                
                                if weight_val > 0:
                                    data.append({
                                        "กลุ่ม/เอเยนต์": group_name, 
                                        "จำนวนคัน": 1,
                                        "น้ำหนักรวม (กก.)": weight_val
                                    })
                
                df_pdf = pd.DataFrame(data)
                if not df_pdf.empty:
                    summary_df = df_pdf.groupby("กลุ่ม/เอเยนต์").agg({
                        "จำนวนคัน": "count",
                        "น้ำหนักรวม (กก.)": "sum"
                    }).reset_index()
                    
                    total_live_bird_all = summary_df["น้ำหนักรวม (กก.)"].sum()
                    total_trucks_all = summary_df["จำนวนคัน"].sum()
                    
                    st.subheader("📊 1.1 สรุปยอดน้ำหนักไก่เป็นรับเข้า")
                    total_row = pd.DataFrame([{
                        "กลุ่ม/เอเยนต์": "Total (รวมทั้งหมด)", 
                        "จำนวนคัน": total_trucks_all,
                        "น้ำหนักรวม (กก.)": total_live_bird_all
                    }])
                    summary_display = pd.concat([summary_df, total_row], ignore_index=True)
                    
                    def highlight_total_1_1(row):
                        if row["กลุ่ม/เอเยนต์"] == "Total (รวมทั้งหมด)": return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
                        return [''] * len(row)
                    
                    # 🚀 เปลี่ยนเป็น st.table เพื่อล็อคตารางไม่ให้เลื่อน
                    st.table(
                        summary_display.style.apply(highlight_total_1_1, axis=1)
                        .format({"จำนวนคัน": "{:,.0f}", "น้ำหนักรวม (กก.)": "{:,.2f}"})
                    )

                    st.divider()
                    st.subheader("📈 1.2 รายละเอียดปริมาณชิ้นส่วนคาดการณ์")
                    
                    agent_list = summary_df["กลุ่ม/เอเยนต์"].tolist()
                    selected_agents_1_2 = st.multiselect("📌 เลือกเอเยนต์ที่ต้องการนำมาคำนวณ Yield:", options=agent_list, default=agent_list)
                    
                    filtered_summary_df = summary_df[summary_df["กลุ่ม/เอเยนต์"].isin(selected_agents_1_2)]

                    yield_results = []
                    for index, row in st.session_state.part_data.iterrows():
                        part = row["รายการ"]
                        rate = row["% Yield"] / 100.0
                        row_data = {"รายการชิ้นส่วน": part, "% Yield": f"{rate*100:.1f}%"}
                        total_expected = 0
                        for _, s_row in filtered_summary_df.iterrows():
                            group = s_row["กลุ่ม/เอเยนต์"]
                            weight = s_row["น้ำหนักรวม (กก.)"]
                            expected_weight = weight * rate
                            row_data[f"กลุ่ม {group} (กก.)"] = expected_weight
                            total_expected += expected_weight
                        
                        row_data["รวมที่เลือก (กก.)"] = total_expected
                        yield_results.append(row_data)

                    yield_df = pd.DataFrame(yield_results)
                    total_yield_row = {"รายการชิ้นส่วน": "Total (รวมสุทธิ)", "% Yield": "105.1%"}
                    for group in filtered_summary_df["กลุ่ม/เอเยนต์"]:
                        total_yield_row[f"กลุ่ม {group} (กก.)"] = yield_df[f"กลุ่ม {group} (กก.)"].sum()
                    total_yield_row["รวมที่เลือก (กก.)"] = yield_df["รวมที่เลือก (กก.)"].sum()
                    
                    yield_display_df = pd.concat([yield_df, pd.DataFrame([total_yield_row])], ignore_index=True)
                    
                    def highlight_total_1_2(row):
                        if row["รายการชิ้นส่วน"] == "Total (รวมสุทธิ)": return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
                        return [''] * len(row)
                    
                    numeric_cols = [col for col in yield_display_df.columns if "(กก.)" in col]
                    
                    # 🚀 เปลี่ยนเป็น st.table เพื่อล็อคตารางไม่ให้เลื่อน
                    st.table(yield_display_df.style.apply(highlight_total_1_2, axis=1).format({col: "{:,.2f}" for col in numeric_cols}))
                    
                    # ปุ่มดาวน์โหลด
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        csv_1_2 = yield_display_df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 ดาวน์โหลดตาราง 1.2 (Excel)",
                            data=csv_1_2,
                            file_name='SFC_Yield_Forecast.csv',
                            mime='text/csv'
                        )
                    with col2:
                        st.info("💡 **ต้องการโหลดเป็น PDF?** กดปุ่ม `Command (⌘) + P` บนคีย์บอร์ด แล้วเลือก **Save as PDF** ได้เลยครับ หน้าตาจะจัดเรียงสวยงามเป๊ะๆ!")

                else:
                    st.error("ไม่พบข้อมูล กรุณาตรวจสอบไฟล์ PDF")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

# ==========================================
# ส่วนที่ 2: จำลองราคาบาลานซ์ชิ้นส่วน (Pricing Module)
# ==========================================
st.divider()
st.header("💰 ส่วนที่ 2: จำลองราคาบาลานซ์ชิ้นส่วน")

m1_df = st.session_state.part_data.copy()
m1_df["รายได้ต่อ 1 กก. (บาท)"] = (m1_df["% Yield"] / 100) * m1_df["ราคาตลาด (บ./กก.)"]
total_revenue_mode1 = m1_df["รายได้ต่อ 1 กก. (บาท)"].sum()
max_live_bird_price = total_revenue_mode1 - factory_cost

st.subheader("🟢 โหมด 1: รู้ราคาตลาด ➔ หาราคาไก่เป็น (หาจุดคุ้มทุน)")
total_row_m1 = pd.DataFrame([{
    "รายการ": "Total (รวมสุทธิ)", "% Yield": 105.1,
    "ราคาตลาด (บ./กก.)": None, "รายได้ต่อ 1 กก. (บาท)": total_revenue_mode1
}])
m1_display = pd.concat([m1_df, total_row_m1], ignore_index=True)

edited_m1_df = st.data_editor(
    m1_display,
    column_config={
        "รายการ": st.column_config.TextColumn(disabled=True),
        "% Yield": st.column_config.NumberColumn(disabled=True, format="%.1f%%"),
        "ราคาตลาด (บ./กก.)": st.column_config.NumberColumn(step=0.5, format="%.2f"),
        "รายได้ต่อ 1 กก. (บาท)": st.column_config.NumberColumn(disabled=True, format="%.4f")
    },
    hide_index=True, 
    use_container_width=True, 
    height=520, # 🚀 ขยายความสูงให้พอดี 12 บรรทัด จะได้ไม่เลื่อน
    key="m1_editor"
)

changed_m1 = False
for i in range(11):
    current_val = edited_m1_df.loc[i, "ราคาตลาด (บ./กก.)"]
    if pd.notna(current_val) and abs(current_val - st.session_state.part_data.loc[i, "ราคาตลาด (บ./กก.)"]) > 0.001:
        st.session_state.part_data.loc[i, "ราคาตลาด (บ./กก.)"] = current_val
        changed_m1 = True
if changed_m1: st.rerun()

st.success(f"**สรุปโหมด 1:** รับซื้อไก่เป็นได้สูงสุด **{max_live_bird_price:,.2f} บาท/กก.** (หักค่าเชือด {factory_cost:,.2f} บ.)")

st.divider()
st.subheader("🎯 โหมด 2: รู้ราคาไก่เป็น ➔ หาราคาขาย (ตารางเดียว Real-time)")
target_total_cost = target_live_bird + factory_cost
st.markdown(f"เป้ารายได้รวม = ไก่ **{target_live_bird:,.2f}** + ค่าเชือด **{factory_cost:,.2f}** = **<span style='color:#d32f2f; font-size:1.2em;'>{target_total_cost:,.2f} บาท/กก.</span>**", unsafe_allow_html=True)

locked_revenue = 0
unlocked_base_revenue = 0
yields = st.session_state.part_data["% Yield"].tolist()
base_prices = st.session_state.part_data["ราคาตลาด (บ./กก.)"].tolist()

for i in range(11):
    y = yields[i] / 100.0
    if st.session_state.m2_locks[i]: locked_revenue += y * st.session_state.m2_lock_prices[i]
    else: unlocked_base_revenue += y * base_prices[i]

remaining_target = target_total_cost - locked_revenue
m2_ratio = remaining_target / unlocked_base_revenue if unlocked_base_revenue > 0 else 0

display_prices = []
display_revenues = []
for i in range(11):
    y = yields[i] / 100.0
    if st.session_state.m2_locks[i]: p = st.session_state.m2_lock_prices[i]
    else: p = base_prices[i] * m2_ratio
    display_prices.append(p)
    display_revenues.append(p * y)

m2_df = pd.DataFrame({
    "รายการชิ้นส่วน": st.session_state.part_data["รายการ"].tolist() + ["Total (รวมสุทธิ)"],
    "% Yield": st.session_state.part_data["% Yield"].tolist() + [105.1],
    "📌 Lock ราคา": st.session_state.m2_locks + [False],
    "ราคาขาย (บ./กก.)": display_prices + [None],
    "รายได้กลับมา (บาท)": display_revenues + [sum(display_revenues)]
})

edited_m2 = st.data_editor(
    m2_df,
    column_config={
        "รายการชิ้นส่วน": st.column_config.TextColumn(disabled=True),
        "% Yield": st.column_config.NumberColumn(disabled=True, format="%.1f%%"),
        "📌 Lock ราคา": st.column_config.CheckboxColumn(),
        "ราคาขาย (บ./กก.)": st.column_config.NumberColumn(step=0.5, format="%.2f"),
        "รายได้กลับมา (บาท)": st.column_config.NumberColumn(disabled=True, format="%.4f")
    },
    hide_index=True, 
    use_container_width=True, 
    height=520, # 🚀 ขยายความสูงให้พอดี 12 บรรทัด จะได้ไม่เลื่อน
    key="m2_editor_realtime"
)

changed = False
for i in range(11):
    if edited_m2.loc[i, "📌 Lock ราคา"] != st.session_state.m2_locks[i]:
        st.session_state.m2_locks[i] = edited_m2.loc[i, "📌 Lock ราคา"]
        if st.session_state.m2_locks[i]:
            val = edited_m2.loc[i, "ราคาขาย (บ./กก.)"]
            if pd.notna(val): st.session_state.m2_lock_prices[i] = val
        changed = True
    
    current_p = edited_m2.loc[i, "ราคาขาย (บ./กก.)"]
    if pd.notna(current_p) and abs(current_p - display_prices[i]) > 0.001:
        st.session_state.m2_lock_prices[i] = current_p
        st.session_state.m2_locks[i] = True  
        changed = True

if changed: st.rerun()  

# ==========================================
# ส่วนที่ 3: สรุปมูลค่าขายคาดการณ์ (ถ้าอัปโหลด PDF)
# ==========================================
if not summary_df.empty:
    st.divider()
    st.subheader("🎯 ส่วนที่ 3: สรุปมูลค่าคาดการณ์ (คำนวณจากน้ำหนัก PDF)")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        agent_options = ["รวมทั้งหมด (Total)"] + summary_df["กลุ่ม/เอเยนต์"].tolist()
        selected_agent = st.selectbox("📌 เลือกเอเยนต์:", agent_options)
        price_mode = st.radio("📌 ใช้ราคาอ้างอิงจาก:", ["โหมด 1 (ราคาตลาด)", "โหมด 2 (ราคาขายเป้าหมาย)"])
    
    if selected_agent == "รวมทั้งหมด (Total)": selected_weight = total_live_bird_all
    else: selected_weight = summary_df[summary_df["กลุ่ม/เอเยนต์"] == selected_agent]["น้ำหนักรวม (กก.)"].values[0]

    with col_b:
        st.info(f"น้ำหนักไก่เป็นที่ใช้คำนวณ: **{selected_weight:,.2f} กก.**")
    
    export_df = pd.DataFrame({
        "รายการชิ้นส่วน": st.session_state.part_data["รายการ"],
        "% Yield": st.session_state.part_data["% Yield"]
    })
    export_df["น้ำหนักผลิตได้ (กก.)"] = (export_df["% Yield"] / 100) * selected_weight
    
    if price_mode == "โหมด 1 (ราคาตลาด)": export_df["ราคาอ้างอิง (บ./กก.)"] = st.session_state.part_data["ราคาตลาด (บ./กก.)"]
    else: export_df["ราคาอ้างอิง (บ./กก.)"] = display_prices
        
    export_df["มูลค่ารวม (บาท)"] = export_df["น้ำหนักผลิตได้ (กก.)"] * export_df["ราคาอ้างอิง (บ./กก.)"]
    grand_total_value = export_df["มูลค่ารวม (บาท)"].sum()
    
    st.success(f"📈 มูลค่าขายคาดการณ์ทั้งหมดของ **{selected_agent}** คือ: **{grand_total_value:,.2f} บาท**")
    
    total_export_row = pd.DataFrame([{
        "รายการชิ้นส่วน": "Total (รวมสุทธิ)", "% Yield": 105.1,
        "น้ำหนักผลิตได้ (กก.)": export_df["น้ำหนักผลิตได้ (กก.)"].sum(),
        "ราคาอ้างอิง (บ./กก.)": None, "มูลค่ารวม (บาท)": grand_total_value
    }])
    export_display = pd.concat([export_df, total_export_row], ignore_index=True)
    
    def highlight_total_p3(row):
        if row["รายการชิ้นส่วน"] == "Total (รวมสุทธิ)": return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)

    # 🚀 เปลี่ยนเป็น st.table เพื่อล็อคตารางไม่ให้เลื่อน
    st.table(export_display.style.apply(highlight_total_p3, axis=1).format({
        "% Yield": "{:.1f}%", "น้ำหนักผลิตได้ (กก.)": "{:,.2f}",
        "ราคาอ้างอิง (บ./กก.)": "{:,.2f}", "มูลค่ารวม (บาท)": "{:,.2f}"
    }, na_rep="-"))

    col3_1, col3_2 = st.columns([1, 2])
    with col3_1:
        csv_3 = export_display.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 ดาวน์โหลดมูลค่า (Excel)",
            data=csv_3,
            file_name=f'SFC_Revenue_{selected_agent}.csv',
            mime='text/csv'
        )
    with col3_2:
        st.info("💡 เซฟหน้าจอนี้เป็นรีพอร์ต PDF สวยๆ: กด `Command (⌘) + P` > เลือก **Save as PDF**")