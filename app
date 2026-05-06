import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Transition Command Center", layout="wide")

# 1. Title and File Upload
st.title("📊 Transition Command Center")
uploaded_file = st.sidebar.file_uploader("Upload Project CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['Start Date'] = pd.to_datetime(df['Start Date'], dayfirst=True)
    df['End Date'] = pd.to_datetime(df['End Date'], dayfirst=True)
    df['Duration'] = (df['End Date'] - df['Start Date']).dt.days

    # 2. Auto 'At Risk' Logic
    def add_risk(row):
        if row['Project Status'] == 'On Track' and row['Progress'] < 0.40:
            return 'At Risk'
        return row['Project Status']
    df['Project Status'] = df.apply(add_risk, axis=1)

    # 3. Sidebar Filters
    locations = ["All"] + sorted(df['Location'].dropna().unique().tolist())
    selected_loc = st.sidebar.selectbox("Step 1: Select Location", locations)

    if selected_loc != "All":
        df = df[df['Location'] == selected_loc]

    statuses = ["All"] + sorted(df['Project Status'].unique().tolist())
    selected_stat = st.sidebar.selectbox("Step 2: Select Status", statuses)

    if selected_stat != "All":
        df = df[df['Project Status'] == selected_stat]

    # 4. Display Dashboard
    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, len(df) * 0.5 + 2))
        colors = {'Behind': '#e74c3c', 'At Risk': '#f39c12', 'On Track': '#2ecc71', 'Completed': '#3498db', 'On Hold': '#95a5a6'}
        
        for i, (idx, row) in enumerate(df.iterrows()):
            color = colors.get(row['Project Status'], 'gray')
            ax.barh(i, row['Duration'], left=row['Start Date'], color=color, edgecolor='black')
            ax.text(row['Start Date'], i, f"  {row['Assigned To']}", va='center', color='white', fontweight='bold')
        
        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['Task Name'])
        st.pyplot(fig)

        # 5. PDF Export
        if st.sidebar.button("Generate PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"TRANSITION REPORT: {selected_loc}", ln=True, align='C')
            
            # Save plot to buffer for PDF
            buf = BytesIO()
            fig.savefig(buf, format="png")
            pdf.image(buf, x=10, w=190)
            
            pdf_output = pdf.output(dest="S").encode("latin-1")
            st.sidebar.download_button(label="Click to Download PDF", data=pdf_output, file_name="Report.pdf", mime="application/pdf")
    else:
        st.warning("No data found for this selection.")
else:
    st.info("Please upload a CSV file to begin.")
