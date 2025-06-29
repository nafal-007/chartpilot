import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio

st.set_page_config(page_title="ChartPilot AI", layout="wide")
st.title("📊 ChartPilot AI")
st.markdown("Upload a CSV or Excel file to visualize your data with smart chart suggestions.")

uploaded_file = st.file_uploader("Choose your data file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("🔍 Data Preview")
    st.dataframe(df.head())

    st.subheader("📈 Chart Options")
    chart_type = st.selectbox("Select Chart Type", [
        "Bar", "Line", "Scatter", "Pie", "Histogram", "Box", "Area", "Heatmap"
    ])
    x_col = st.selectbox("Select X-axis", df.columns)
    y_col = None
    if chart_type not in ["Pie", "Histogram"]:
        y_col = st.selectbox("Select Y-axis", df.columns)

    if st.button("Generate Chart"):
        fig = None
        if chart_type == "Bar":
            fig = px.bar(df, x=x_col, y=y_col)
        elif chart_type == "Line":
            fig = px.line(df, x=x_col, y=y_col)
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x_col, y=y_col)
        elif chart_type == "Pie":
            fig = px.pie(df, names=x_col)
        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_col)
        elif chart_type == "Box":
            fig = px.box(df, x=x_col, y=y_col)
        elif chart_type == "Area":
            fig = px.area(df, x=x_col, y=y_col)
        elif chart_type == "Heatmap":
            fig = px.density_heatmap(df, x=x_col, y=y_col)

        st.plotly_chart(fig, use_container_width=True)

        png_bytes = pio.to_image(fig, format="png")
        st.download_button("Download Chart as PNG", png_bytes, file_name="chart.png")