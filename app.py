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
# Using the raw URL for your specific repository
GITHUB_RAW_URL = "https://githubusercontent.com"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    df['Start Date'] = pd.to_datetime(df['Start Date'], dayfirst=True)
    df['End Date'] = pd.to_datetime(df['End Date'], dayfirst=True)
    df['Duration'] = (df['End Date'] - df['Start Date']).dt.days
    return df

# --- CUSTOM PDF CLASS ---
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
        # Check connection status
        response = requests.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            df_raw = load_data(GITHUB_RAW_URL)
            st.sidebar.success("✅ Connected to GitHub Data")
        else:
            st.sidebar.error(f"❌ GitHub Connection Failed (Error {response.status_code})")
            st.info("Ensure the file name is 'Project Management.csv' and the repo is Public.")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Error: {e}")
else:
    uploaded_file = st.sidebar.file_uploader("Upload Project Management CSV", type=["csv"])
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file)
        # Pre-process uploaded data
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
        st.subheader(f"Current Dashboard: {selected_loc} | {selected_stat}")
        
        fig, ax = plt.subplots(figsize=(10, len(df_final) * 0.5 + 2))
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
            pdf.add_page()
            
            # Sub-header
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Filter View: {selected_loc} / {selected_stat}", ln=True)
            
            # Insert Dashboard Image
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            pdf.image(buf, x=15, y=45, w=180)
            
            # Action Table
            pdf.set_y(160)
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(90, 10, "Task", 1, 0, 'C', True)
            pdf.cell(40, 10, "Owner", 1, 0, 'C', True)
            pdf.cell(30, 10, "Progress", 1, 0, 'C', True)
            pdf.cell(30, 10, "Status", 1, 1, 'C', True)
            
            pdf.set_font("Arial", '', 8)
            for _, r in df_final.head(12).iterrows():
                # Use multi_cell to prevent text hiding
                x, y = pdf.get_x(), pdf.get_y()
                pdf.multi_cell(90, 8, str(r['Task Name']), 1)
                pdf.set_xy(x + 90, y)
                pdf.cell(40, 8, str(r['Assigned To']), 1, 0, 'C')
                pdf.cell(30, 8, f"{int(r['Progress']*100)}%", 1, 0, 'C')
                pdf.cell(30, 8, str(r['Project Status']), 1, 1, 'C')

            # Final Output
            pdf_bytes = pdf.output()
            if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin-1')
            else: pdf_bytes = bytes(pdf_bytes)

            st.sidebar.download_button(
                label="✅ Download PDF Report", 
                data=pdf_bytes, 
                file_name=f"Transition_Report_{selected_loc}.pdf", 
                mime="application/pdf"
            )
    else:
        st.warning("No data found for this selection.")
else:
    st.info("Please select a data source or upload your CSV to begin.")
