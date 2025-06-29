import base64

# ---------------- Chart Generation ----------------
if st.button("uploaded_file = st.file_uploader("Choose your data file", type=["csv", "xlsx"])

if uploaded_file:
    # Load data
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("🔍 Data Preview")
    st.dataframe(df.head())

    # Chart options
    st.subheader("📈 Chart Options")
    chart_type = st.selectbox("Select Chart Type", [
        "Bar", "Line", "Scatter", "Pie", "Histogram", "Box", "Area", "Heatmap"
    ])

    x_col = st.selectbox("Select X-axis", df.columns)
    y_col = None
    if chart_type not in ["Pie", "Histogram"]:
        y_col = st.selectbox("Select Y-axis", df.columns)

    # ✅ Only place this inside the uploaded_file check
    if st.button("Generate Chart"):
        # Your chart generation and download code here
        ...
"):
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

    # Show the chart
    st.plotly_chart(fig, use_container_width=True)

    # HTML Export (safe for Streamlit Cloud)
    html_bytes = fig.to_html(full_html=False).encode("utf-8")
    b64 = base64.b64encode(html_bytes).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="chart.html">📥 Download Chart as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
