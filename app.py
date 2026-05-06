import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from io import BytesIO
import requests

# --- PAGE CONFIG ---
st.set_page_config(page_title="Transition Command Center", layout="wide")

# --- GITHUB DATA SOURCE ---
# Correct RAW URL for your specific repository and filename
# GITHUB_RAW_URL = "https://githubusercontent.com"
GITHUB_RAW_URL = "https://github.com/SRINIVASTA/Transition-Command-Center/blob/main/Project%20Management.csv"

@st.cache_data
def load_github_data(url):
    df = pd.read_csv(url)
    df['Start Date'] = pd.to_datetime(df['Start Date'], dayfirst=True)
    df['End Date'] = pd.to_datetime(df['End Date'], dayfirst=True)
    df['Duration'] = (df['End Date'] - df['Start Date']).dt.days
    return df

# --- CUSTOM PDF CLASS WITH BORDER & TIMESTAMP ---
class TransitionPDF(FPDF):
    def header(self):
        # Professional Page Border
        self.set_line_width(0.5)
        self.rect(5, 5, 200, 287) 
        
        # Last Updated Timestamp
        self.set_font('Arial', 'I', 8)
        timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")
        self.set_xy(10, 10)
        self.cell(0, 10, f'Report Generated: {timestamp}', 0, 1, 'R')
        
        # Report Title
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'TRANSITION COMPLETION REPORT', 0, 1, 'C')
        self.ln(5)

# --- APP LOGIC ---
st.title("📊 Transition Command Center")

# Choose Data Connection
data_mode = st.sidebar.radio("📁 Select Data Source:", ("Live GitHub Data", "Manual Upload (CSV)"))

df_raw = None

if data_mode == "Live GitHub Data":
    try:
        # Check connection status first
        response = requests.get(GITHUB_RAW_URL, timeout=5)
        if response.status_code == 200:
            df_raw = load_github_data(GITHUB_RAW_URL)
            st.sidebar.success("✅ Connected to GitHub Data")
        else:
            st.sidebar.error(f"❌ Connection Failed (Error {response.status_code})")
            st.info("Check if the file on GitHub is exactly: Project Management.csv")
    except Exception as e:
        st.sidebar.error("❌ Connection Error: Ensure URL starts with '://githubusercontent.com'")
else:
    uploaded_file = st.sidebar.file_uploader("Upload Project Management CSV", type=["csv"])
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        df_raw['Start Date'] = pd.to_datetime(df_raw['Start Date'], dayfirst=True)
        df_raw['End Date'] = pd.to_datetime(df_raw['End Date'], dayfirst=True)
        df_raw['Duration'] = (df_raw['End Date'] - df_raw['Start Date']).dt.days
        st.sidebar.success("✅ File Uploaded Successfully")

# Process and Display if data is available
if df_raw is not None:
    # Auto 'At Risk' Logic (The 5th Status)
    def add_risk(row):
        if row['Project Status'] == 'On Track' and row['Progress'] < 0.40:
            return 'At Risk'
        return row['Project Status']
    df_raw['Project Status'] = df_raw.apply(add_risk, axis=1)

    # Sidebar Filters
    locations = ["All"] + sorted(df_raw['Location'].dropna().unique().tolist())
    selected_loc = st.sidebar.selectbox("Filter 1: Location", locations)
    df_filtered = df_raw.copy() if selected_loc == "All" else df_raw[df_raw['Location'] == selected_loc]

    statuses = ["All"] + sorted(df_filtered['Project Status'].unique().tolist())
    selected_stat = st.sidebar.selectbox("Filter 2: Status", statuses)
    df_final = df_filtered.copy() if selected_stat == "All" else df_filtered[df_filtered['Project Status'] == selected_stat]

    # --- DESKTOP VIEW ---
    if not df_final.empty:
        st.subheader(f"Monitoring Dashboard: {selected_loc} | {selected_stat}")
        
        # Increase figure size based on task count
        fig, ax = plt.subplots(figsize=(12, len(df_final) * 0.6 + 2))
        colors = {'Behind': '#e74c3c', 'At Risk': '#f39c12', 'On Track': '#2ecc71', 'Completed': '#3498db', 'On Hold': '#95a5a6'}
        
        for i, (idx, row) in enumerate(df_final.iterrows()):
            color = colors.get(row['Project Status'], 'gray')
            ax.barh(i, row['Duration'], left=row['Start Date'], color=color, edgecolor='black')
            # Names inside the bars
            ax.text(row['Start Date'], i, f"  {row['Assigned To']}", va='center', color='white', fontweight='bold', fontsize=9)
        
        ax.set_yticks(range(len(df_final)))
        ax.set_yticklabels(df_final['Task Name'])
        st.pyplot(fig)

        # --- PDF EXPORT ---
        st.sidebar.markdown("---")
        if st.sidebar.button("📄 Generate PDF Report"):
            pdf = TransitionPDF()
            
            # --- PAGE 1: Gantt Chart ---
            pdf.add_page()
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Filter View: {selected_loc} / {selected_stat}", ln=True)
            
            # Insert Chart Image
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            pdf.image(buf, x=15, y=45, w=180)
            
            # --- PAGE 2: Action Table ---
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Critical Action Items & Status Summary", ln=True, align='C')
            pdf.ln(5)
            
            # Table Header
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(90, 10, "Task Name", 1, 0, 'C', True)
            pdf.cell(40, 10, "Owner", 1, 0, 'C', True)
            pdf.cell(30, 10, "Progress", 1, 0, 'C', True)
            pdf.cell(30, 10, "Status", 1, 1, 'C', True)
            
            # Table Rows (Using multi_cell for wrapping long text)
            pdf.set_font("Arial", '', 8)
            for _, r in df_final.iterrows():
                curr_x, curr_y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(90, 10, str(r['Task Name']), 1)
                pdf.set_xy(curr_x + 90, curr_y)
                pdf.cell(40, 10, str(r['Assigned To']), 1, 0, 'C')
                pdf.cell(30, 10, f"{int(r['Progress']*100)}%", 1, 0, 'C')
                pdf.cell(30, 10, str(r['Project Status']), 1, 1, 'C')

            # Final Output Generation
            pdf_bytes = pdf.output()
            # Handle version differences in fpdf2 output
            if isinstance(pdf_bytes, str):
                final_bytes = pdf_bytes.encode('latin-1')
            else:
                final_bytes = bytes(pdf_bytes)

            st.sidebar.download_button(
                label="✅ Download PDF Report", 
                data=final_bytes, 
                file_name=f"Transition_Report_{selected_loc}.pdf", 
                mime="application/pdf"
            )
            st.sidebar.success("PDF Ready!")
    else:
        st.warning("No data found for this selection.")
else:
    st.info("Select a data source in the sidebar to begin monitoring.")
