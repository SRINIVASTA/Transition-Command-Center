import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Transition Command Center", layout="wide")

# --- CUSTOM PDF CLASS ---
class TransitionPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'I', 8)
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        self.cell(0, 10, f'Report Generated: {timestamp}', 0, 1, 'R')
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'TRANSITION COMPLETION REPORT', 0, 1, 'C')
        self.ln(5)

# --- APP LOGIC ---
st.title("📊 Transition Command Center")
uploaded_file = st.sidebar.file_uploader("Step 1: Upload Project CSV", type=["csv"])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
    df_raw['Start Date'] = pd.to_datetime(df_raw['Start Date'], dayfirst=True)
    df_raw['End Date'] = pd.to_datetime(df_raw['End Date'], dayfirst=True)
    df_raw['Duration'] = (df_raw['End Date'] - df_raw['Start Date']).dt.days

    # Auto 'At Risk' Logic (The 5th Status)
    def add_risk(row):
        if row['Project Status'] == 'On Track' and row['Progress'] < 0.40:
            return 'At Risk'
        return row['Project Status']
    df_raw['Project Status'] = df_raw.apply(add_risk, axis=1)

    # Sidebar Filters
    locations = ["All"] + sorted(df_raw['Location'].dropna().unique().tolist())
    selected_loc = st.sidebar.selectbox("Step 2: Select Location", locations)
    df_filtered = df_raw.copy() if selected_loc == "All" else df_raw[df_raw['Location'] == selected_loc]

    statuses = ["All"] + sorted(df_filtered['Project Status'].unique().tolist())
    selected_stat = st.sidebar.selectbox("Step 3: Select Status", statuses)
    df_final = df_filtered.copy() if selected_stat == "All" else df_filtered[df_filtered['Project Status'] == selected_stat]

    # --- DASHBOARD DISPLAY ---
    if not df_final.empty:
        st.subheader(f"Dashboard: {selected_loc} | Status: {selected_stat}")
        fig, ax = plt.subplots(figsize=(10, len(df_final) * 0.5 + 2))
        colors = {'Behind': '#e74c3c', 'At Risk': '#f39c12', 'On Track': '#2ecc71', 'Completed': '#3498db', 'On Hold': '#95a5a6'}
        
        for i, (idx, row) in enumerate(df_final.iterrows()):
            color = colors.get(row['Project Status'], 'gray')
            ax.barh(i, row['Duration'], left=row['Start Date'], color=color, edgecolor='black')
            ax.text(row['Start Date'], i, f"  {row['Assigned To']}", va='center', color='white', fontweight='bold')
        
        ax.set_yticks(range(len(df_final)))
        ax.set_yticklabels(df_final['Task Name'])
        st.pyplot(fig)

        # --- PDF EXPORT SECTION ---
        if st.sidebar.button("📄 Generate PDF Report"):
            pdf = TransitionPDF()
            
            # PAGE 1: Roadmap & Table
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Filter View: {selected_loc} / {selected_stat}", ln=True)
            
            # Roadmap Image
            buf_gantt = BytesIO()
            fig.savefig(buf_gantt, format="png", bbox_inches='tight')
            buf_gantt.seek(0)
            pdf.image(buf_gantt, x=10, y=40, w=190)
            
            # Task Table
            pdf.set_y(150)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(90, 10, "Task", 1); pdf.cell(30, 10, "Status", 1); pdf.cell(40, 10, "Owner", 1); pdf.cell(30, 10, "Progress", 1); pdf.ln()
            pdf.set_font("Arial", '', 8)
            for _, r in df_final.head(10).iterrows():
                pdf.cell(90, 10, str(r['Task Name'])[:45], 1); pdf.cell(30, 10, str(r['Project Status']), 1); 
                pdf.cell(40, 10, str(r['Assigned To']), 1); pdf.cell(30, 10, f"{int(r['Progress']*100)}%", 1); pdf.ln()

            # PAGE 2: Summary Charts
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Project Status Distribution Summary", ln=True, align='C')
            
            fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
            df_final['Project Status'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax_pie, colors=[colors.get(x, 'gray') for x in df_final['Project Status'].unique()])
            buf_pie = BytesIO()
            fig_pie.savefig(buf_pie, format="png", bbox_inches='tight')
            buf_pie.seek(0)
            pdf.image(buf_pie, x=50, y=40, w=110)

            # Finalize Output
            pdf_bytes = pdf.output()
            if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin-1')
            else: pdf_bytes = bytes(pdf_bytes)

            st.sidebar.download_button(label="✅ Click to Download PDF", data=pdf_bytes, file_name=f"Report_{selected_loc}.pdf", mime="application/pdf")
    else:
        st.warning("No data found.")
else:
    st.info("Upload 'Project Management.csv' to start.")
