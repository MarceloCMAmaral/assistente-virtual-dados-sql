"""
Dynamic visualization module using Plotly.
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from io import StringIO

from src.config import Config


def detect_visualization_type(df: pd.DataFrame) -> str:
    """
    Detect the best visualization type based on data characteristics.
    
    Args:
        df: DataFrame to analyze.
        
    Returns:
        str: Visualization type ("bar", "line", "scatter", "histogram", "pie", "table").
    """
    if df.empty:
        return "empty"
    
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # Try to detect date columns
    date_cols = []
    for col in cat_cols:
        try:
            pd.to_datetime(df[col])
            date_cols.append(col)
        except (ValueError, TypeError):
            pass
    
    # Remove date columns from categorical columns
    cat_cols = [c for c in cat_cols if c not in date_cols]
    
    # Decision rules
    if len(date_cols) > 0 and len(num_cols) > 0:
        return "line"  # Time series
    
    if len(cat_cols) > 0 and len(num_cols) > 0:
        if len(df) <= Config.MAX_BARS_CHART:
            # Check if it could be a pie chart (single category, single value)
            if len(df) <= 6 and len(cat_cols) == 1 and len(num_cols) == 1:
                return "pie"
            return "bar"
        else:
            return "table"
    
    if len(num_cols) >= 2:
        return "scatter"
    
    if len(num_cols) == 1 and len(df) > Config.MIN_ROWS_HISTOGRAM:
        return "histogram"
    
    return "table"


def parse_query_result(result: str) -> pd.DataFrame:
    """
    Parse query result string into a DataFrame.
    
    Args:
        result: Query result as string (SQLite format).
        
    Returns:
        pd.DataFrame: Parsed data.
    """
    if not result or result.strip() == "":
        return pd.DataFrame()
    
    # SQLite returns results in a specific format
    # Try to parse as a list of tuples representation
    try:
        # Check if result looks like a list of tuples
        if result.strip().startswith("[") and result.strip().endswith("]"):
            import ast
            data = ast.literal_eval(result)
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], tuple):
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame({"resultado": data})
    except:
        pass
    
    # Try to parse as CSV
    try:
        df = pd.read_csv(StringIO(result))
        return df
    except:
        pass
    
    # Return as single column if nothing works
    try:
        lines = result.strip().split('\n')
        return pd.DataFrame({"resultado": lines})
    except:
        return pd.DataFrame()


def display_data(result: str | pd.DataFrame, force_type: str = None) -> None:
    """
    Display data with appropriate visualization.
    
    Args:
        result: Query result (string or DataFrame).
        force_type: Force a specific visualization type.
    """
    # Convert to DataFrame if needed
    if isinstance(result, str):
        df = parse_query_result(result)
    else:
        df = result
    
    if df.empty:
        st.info("Nenhum resultado encontrado.")
        return
    
    # Detect or use forced visualization type
    viz_type = force_type or detect_visualization_type(df)
    
    # For simple tables, just show the data
    if viz_type == "table" or viz_type == "empty":
        st.dataframe(df, use_container_width=True)
        return
    
    # Create tabs for chart and data
    tab_chart, tab_data = st.tabs(["Grafico", "Dados"])
    
    with tab_chart:
        try:
            if viz_type == "bar":
                _render_bar_chart(df)
            elif viz_type == "line":
                _render_line_chart(df)
            elif viz_type == "scatter":
                _render_scatter_chart(df)
            elif viz_type == "histogram":
                _render_histogram(df)
            elif viz_type == "pie":
                _render_pie_chart(df)
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.warning(f"Nao foi possivel gerar o grafico: {e}")
            st.dataframe(df, use_container_width=True)
    
    with tab_data:
        st.dataframe(df, use_container_width=True)


def _render_bar_chart(df: pd.DataFrame) -> None:
    """Render a bar chart."""
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if not cat_cols or not num_cols:
        st.dataframe(df, use_container_width=True)
        return
    
    x_col = cat_cols[0]
    y_col = num_cols[0]
    
    fig = px.bar(
        df, 
        x=x_col, 
        y=y_col,
        title=f"{y_col} por {x_col}",
        color=x_col if len(df) <= 10 else None,
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def _render_line_chart(df: pd.DataFrame) -> None:
    """Render a line chart for time series."""
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    # Find date column
    date_col = None
    for col in cat_cols:
        try:
            df[col] = pd.to_datetime(df[col])
            date_col = col
            break
        except:
            pass
    
    if date_col is None or not num_cols:
        st.dataframe(df, use_container_width=True)
        return
    
    y_col = num_cols[0]
    
    fig = px.line(
        df, 
        x=date_col, 
        y=y_col,
        title=f"Tendencia de {y_col}",
        markers=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_scatter_chart(df: pd.DataFrame) -> None:
    """Render a scatter plot."""
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if len(num_cols) < 2:
        st.dataframe(df, use_container_width=True)
        return
    
    fig = px.scatter(
        df, 
        x=num_cols[0], 
        y=num_cols[1],
        title=f"{num_cols[1]} vs {num_cols[0]}",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_histogram(df: pd.DataFrame) -> None:
    """Render a histogram."""
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if not num_cols:
        st.dataframe(df, use_container_width=True)
        return
    
    fig = px.histogram(
        df, 
        x=num_cols[0],
        title=f"Distribuicao de {num_cols[0]}",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_pie_chart(df: pd.DataFrame) -> None:
    """Render a pie chart."""
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if not cat_cols or not num_cols:
        st.dataframe(df, use_container_width=True)
        return
    
    fig = px.pie(
        df, 
        names=cat_cols[0], 
        values=num_cols[0],
        title=f"Proporcao de {num_cols[0]} por {cat_cols[0]}",
    )
    st.plotly_chart(fig, use_container_width=True)
