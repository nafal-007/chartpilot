from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response
import pandas as pd
import plotly.express as px
import plotly.io as pio
import json
import io
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# In-memory store for the current dataframe (for demo/single user purposes)
# In production, you'd save it to a database or temp file per session.
current_df = None


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global current_df
    try:
        content = await file.read()
        if file.filename.endswith(".csv"):
            try:
                current_df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    current_df = pd.read_csv(io.BytesIO(content), encoding="cp1252")
                except UnicodeDecodeError:
                    current_df = pd.read_csv(io.BytesIO(content), encoding="latin1")
        elif file.filename.endswith(".xlsx"):
            current_df = pd.read_excel(io.BytesIO(content))
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid file format"})
            
        # Strip invisible whitespace from column headers to prevent silent KeyErrors in grouping
        current_df.columns = current_df.columns.str.strip()
        
        # Cache dataset to local disk for cross-worker cloud persistence
        current_df.to_csv("dataset_cache.csv", index=False)
        
        # Calculate Data Quality Metrics
        total_rows = len(current_df)
        total_cols = len(current_df.columns)
        missing_values = current_df.isnull().sum().to_dict()
        duplicate_rows = current_df.duplicated().sum()
        
        # Send back headers for subsequent charting
        columns = current_df.columns.tolist()

        return {
            "message": "File uploaded successfully",
            "columns": columns,
            "quality": {
                "total_rows": total_rows,
                "total_cols": total_cols,
                "duplicate_rows": int(duplicate_rows),
                "missing_values": missing_values
            },
            "preview": current_df.head(15).fillna("NaN").to_dict(orient="records")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/clean")
async def clean_data(action: str = Form(...)):
    global current_df
    if current_df is None:
        if os.path.exists("dataset_cache.csv"):
            current_df = pd.read_csv("dataset_cache.csv")
    if current_df is None:
        return JSONResponse(status_code=400, content={"error": "No dataset uploaded"})
    
    try:
        if action == "drop_duplicates":
            current_df = current_df.drop_duplicates()
        elif action == "drop_na":
            current_df = current_df.dropna()
        elif action == "fill_mean":
            # Fill only numeric columns with their mean
            numeric_cols = current_df.select_dtypes(include='number').columns
            current_df[numeric_cols] = current_df[numeric_cols].fillna(current_df[numeric_cols].mean())
        elif action == "fill_zero":
            current_df = current_df.fillna(0)
        
        # Recalculate metrics
        total_rows = len(current_df)
        total_cols = len(current_df.columns)
        missing_values = current_df.isnull().sum().to_dict()
        duplicate_rows = current_df.duplicated().sum()

        # Cache the cleaned dataset
        current_df.to_csv("dataset_cache.csv", index=False)

        return {
            "message": f"Action {action} applied.",
            "quality": {
                "total_rows": total_rows,
                "total_cols": total_cols,
                "duplicate_rows": int(duplicate_rows),
                "missing_values": missing_values
            },
            "preview": current_df.head(15).fillna("NaN").to_dict(orient="records")
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/plot")
async def generate_plot(
    chart_type: str = Form(...),
    x_col: str = Form(...),
    y_col: str = Form(None),
    color_col: str = Form(None),
    aggregation: str = Form(None)
):
    global current_df
    if current_df is None:
        if os.path.exists("dataset_cache.csv"):
            current_df = pd.read_csv("dataset_cache.csv")
            
    if current_df is None:
        return JSONResponse(status_code=400, content={"error": "No dataset uploaded yet. The backend was hot-reloaded! Please click 'Upload File' to reload your data."})
    
    try:
        fig = None
        
        color_arg = color_col if color_col and color_col != "None" else None

        # Determine if we have Y axis depending on chart type
        y_arg = y_col if y_col and y_col != "None" else None

        # Process Data Aggregations if applicable
        plot_df = current_df.copy()
        agg_method = aggregation if aggregation and aggregation != "None" else None

        if agg_method:
            group_cols = [x_col]
            if color_arg:
                group_cols.append(color_arg)
                
            if not y_arg or (y_arg and not pd.api.types.is_numeric_dtype(plot_df[y_arg]) and agg_method != "Count"):
                # Graceful fallback: Default to Count frequencies for invalid mathematical operations
                plot_df = plot_df.groupby(group_cols, as_index=False).size()
                plot_df.rename(columns={"size": "Count"}, inplace=True)
                y_arg = "Count"
                agg_method = "Count"
            elif y_arg and pd.api.types.is_numeric_dtype(plot_df[y_arg]):
                if agg_method == "Sum":
                    plot_df = plot_df.groupby(group_cols, as_index=False)[y_arg].sum()
                elif agg_method == "Average":
                    plot_df = plot_df.groupby(group_cols, as_index=False)[y_arg].mean()
                elif agg_method == "Count":
                    plot_df = plot_df.groupby(group_cols, as_index=False)[y_arg].count()
                elif agg_method == "Min":
                    plot_df = plot_df.groupby(group_cols, as_index=False)[y_arg].min()
                elif agg_method == "Max":
                    plot_df = plot_df.groupby(group_cols, as_index=False)[y_arg].max()
                    
        # Fallback for single-column Pie/Scatter charts (count frequencies if no Y is provided to avoid invisible 1D lines)
        if chart_type in ["Pie", "Scatter"] and not y_arg:
            plot_df = plot_df.groupby([x_col], as_index=False).size()
            plot_df.rename(columns={"size": "Count"}, inplace=True)
            y_arg = 'Count'
            
        # Prevent SVG rendering freezes by intelligently binning excessive Pie slices > 15 into 'Other'
        if chart_type == "Pie" and len(plot_df) > 15:
            plot_df = plot_df.sort_values(by=y_arg, ascending=False)
            top_15 = plot_df.iloc[:15].copy()
            others_sum = plot_df.iloc[15:][y_arg].sum()
            others_row = pd.DataFrame([{x_col: 'Other', y_arg: others_sum}])
            if color_arg:
                 others_row[color_arg] = 'Mixed'
            plot_df = pd.concat([top_15, others_row], ignore_index=True)

        # Build dynamic title
        title_text = f"{chart_type} Chart: {x_col}"
        if y_arg:
            title_text += f" vs {y_arg}"
        if color_arg:
            title_text += f" (grouped by {color_arg})"

        if chart_type == "Bar":
            fig = px.bar(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text)
        elif chart_type == "Line":
            fig = px.line(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text, markers=True)
        elif chart_type == "Scatter":
            fig = px.scatter(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text, size_max=15)
        elif chart_type == "Pie":
            fig = px.pie(plot_df, names=x_col, values=y_arg, color=color_arg, template="plotly_dark", title=title_text, hole=0.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
        elif chart_type == "Histogram":
            fig = px.histogram(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text, marginal="box")
        elif chart_type == "Box":
            fig = px.box(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text, points="all")
        elif chart_type == "Area":
            fig = px.area(plot_df, x=x_col, y=y_arg, color=color_arg, template="plotly_dark", title=title_text)
            
        if not fig:
             return JSONResponse(status_code=400, content={"error": "Invalid Chart Configuration"})

        # Enhance Layout for more detailed visualization
        fig.update_layout(
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0.02)',
            font={"family": "Manrope, sans-serif", "size": 13, "color": "rgba(255,255,255,0.85)"},
            hovermode="x unified",
            title_x=0.5,
            xaxis={"showgrid": True, "gridcolor": 'rgba(255,255,255,0.05)', "zerolinecolor": 'rgba(255,255,255,0.1)'},
            yaxis={"showgrid": True, "gridcolor": 'rgba(255,255,255,0.05)', "zerolinecolor": 'rgba(255,255,255,0.1)'}
        )
        if chart_type == "Pie":
            fig.update_layout(hovermode="closest")

        graph_json = pio.to_json(fig)
        return Response(content='{"graph_json": ' + graph_json + '}', media_type="application/json")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
