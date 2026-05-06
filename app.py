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
        # Adding a "Last Updated" timestamp to the top right of the report
        self.set_font('Arial', 'I', 8)
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        self.cell(0, 10, f'Report Generated: {timestamp}', 0, 1, 'R')
        
        # Main Title
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'TRANSITION COMPLETION REPORT', 0, 1, 'C')
        self.ln(5)

# --- APP LOGIC ---
st.title("📊 Transition Command Center")
uploaded_file = st.sidebar.file_uploader("Step 1: Upload Project CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['Start Date'] = pd.to_datetime(df['Start Date'], dayfirst=True)
    df['End Date'] = pd.to_datetime(df['End Date'], dayfirst=True)
    df['Duration'] = (df['End Date'] - df['Start Date']).dt.days

    # Auto 'At Risk' Logic (The 5th Status)
    def add_risk(row):
        if row['Project Status'] == 'On Track' and row['Progress'] < 0.40:
            return 'At Risk'
        return row['Project Status']
    df['Project Status'] = df.apply(add_risk, axis=1)

    # Sidebar Filters
    locations = ["All"] + sorted(df['Location'].dropna().unique().tolist())
    selected_loc = st.sidebar.selectbox("Step 2: Select Location", locations)

    if selected_loc != "All":
        df = df[df['Location'] == selected_loc].copy()

    statuses = ["All"] + sorted(df['Project Status'].unique().tolist())
    selected_stat = st.sidebar.selectbox("Step 3: Select Status", statuses)

    if selected_stat != "All":
        df = df[df['Project Status'] == selected_stat].copy()

    # --- DASHBOARD DISPLAY ---
    if not df.empty:
        st.subheader(f"Dashboard: {selected_loc} | Status: {selected_stat}")
        
        fig, ax = plt.subplots(figsize=(10, len(df) * 0.5 + 2))
        colors = {'Behind': '#e74c3c', 'At Risk': '#f39c12', 'On Track': '#2ecc71', 'Completed': '#3498db', 'On Hold': '#95a5a6'}
        
        for i, (idx, row) in enumerate(df.iterrows()):
            color = colors.get(row['Project Status'], 'gray')
            ax.barh(i, row['Duration'], left=row['Start Date'], color=color, edgecolor='black')
            # Text inside the bars
            ax.text(row['Start Date'], i, f"  {row['Assigned To']}", va='center', color='white', fontweight='bold')
        
        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['Task Name'])
        st.pyplot(fig)

        # --- PDF EXPORT SECTION ---
        st.sidebar.markdown("---")
        if st.sidebar.button("📄 I want to generate a PDF report?"):
            pdf = TransitionPDF()
            pdf.add_page()
            
            # Sub-header for the filter view
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Filter View: {selected_loc} / {selected_stat}", ln=True)
            
            # Save plot to buffer as a PNG image
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            
            # Insert the image from memory buffer
            pdf.image(buf, x=10, y=40, w=190)
            
            # Table Header
            pdf.ln(110)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(90, 10, "Task", 1); pdf.cell(30, 10, "Status", 1); pdf.cell(40, 10, "Owner", 1); pdf.cell(30, 10, "Progress", 1)
            pdf.ln()
            
            # Table Rows
            pdf.set_font("Arial", '', 8)
            for _, row in df.iterrows():
                pdf.cell(90, 10, str(row['Task Name'])[:45], 1)
                pdf.cell(30, 10, str(row['Project Status']), 1)
                pdf.cell(40, 10, str(row['Assigned To']), 1)
                pdf.cell(30, 10, f"{int(row['Progress']*100)}%", 1)
                pdf.ln()
            
            # Output the PDF as bytes
            pdf_bytes = pdf.output() 
            st.sidebar.download_button(
                label="✅ Click to Download PDF", 
                data=pdf_bytes, 
                file_name=f"Report_{selected_loc}.pdf", 
                mime="application/pdf"
            )
            st.sidebar.success("PDF ready for download!")
    else:
        st.warning("No data found for this selection.")
else:
    st.info("Please upload your 'Project Management.csv' file to begin.")
