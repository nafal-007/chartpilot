import base64

# ---------------- Chart Generation ----------------
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

    # Show the chart
    st.plotly_chart(fig, use_container_width=True)

    # HTML Export (safe for Streamlit Cloud)
    html_bytes = fig.to_html(full_html=False).encode("utf-8")
    b64 = base64.b64encode(html_bytes).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="chart.html">📥 Download Chart as HTML</a>'
    st.markdown(href, unsafe_allow_html=True)
