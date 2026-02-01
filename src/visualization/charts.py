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


def parse_query_result(result: str, query: str = None) -> pd.DataFrame:
    """
    Parse query result string into a DataFrame.
    
    Args:
        result: Query result as string (SQLite format).
        query: Optional SQL query to extract column names from.
        
    Returns:
        pd.DataFrame: Parsed data with proper column names.
    """
    if not result or result.strip() == "":
        return pd.DataFrame()
    
    # Try to extract column names from query
    column_names = _extract_column_names_from_query(query) if query else None
    
    # SQLite returns results in a specific format
    # Try to parse as a list of tuples representation
    try:
        # Check if result looks like a list of tuples
        if result.strip().startswith("[") and result.strip().endswith("]"):
            import ast
            data = ast.literal_eval(result)
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], tuple):
                    df = pd.DataFrame(data)
                    # Apply column names if available
                    if column_names and len(column_names) == len(df.columns):
                        df.columns = column_names
                    else:
                        # Generate meaningful default names
                        df.columns = _generate_column_names(df)
                    return df
                else:
                    return pd.DataFrame({"Resultado": data})
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
        return pd.DataFrame({"Resultado": lines})
    except:
        return pd.DataFrame()


def _extract_column_names_from_query(query: str) -> list[str] | None:
    """
    Try to extract column names from a SQL SELECT query.
    
    Args:
        query: SQL query string.
        
    Returns:
        List of column names or None if extraction fails.
    """
    if not query:
        return None
    
    try:
        query_upper = query.upper()
        
        # Find SELECT ... FROM
        select_idx = query_upper.find("SELECT")
        from_idx = query_upper.find("FROM")
        
        if select_idx == -1 or from_idx == -1:
            return None
        
        select_clause = query[select_idx + 6:from_idx].strip()
        
        # Handle SELECT *
        if select_clause.strip() == "*":
            return None
        
        # Split by comma and extract column names/aliases
        columns = []
        for part in select_clause.split(","):
            part = part.strip()
            
            # Handle AS aliases
            if " AS " in part.upper():
                alias_idx = part.upper().find(" AS ")
                alias = part[alias_idx + 4:].strip().strip('"').strip("'")
                columns.append(alias)
            elif " as " in part:
                alias_idx = part.find(" as ")
                alias = part[alias_idx + 4:].strip().strip('"').strip("'")
                columns.append(alias)
            else:
                # Use the column name or function result
                # Handle functions like COUNT(*), SUM(valor)
                if "(" in part:
                    # Extract function name for display
                    func_name = part.split("(")[0].strip()
                    columns.append(func_name.capitalize())
                else:
                    # Clean up column name
                    col_name = part.split(".")[-1].strip()  # Handle table.column
                    columns.append(col_name)
        
        return columns if columns else None
    except:
        return None


def _generate_column_names(df: pd.DataFrame) -> list[str]:
    """
    Generate meaningful column names based on data types.
    
    Args:
        df: DataFrame with numeric column indices.
        
    Returns:
        List of column names.
    """
    names = []
    for i, col in enumerate(df.columns):
        # Check data type of column
        if df[col].dtype in ['int64', 'float64']:
            # Check if it looks like a count or value
            if df[col].max() > 1000:
                names.append(f"Valor_{i+1}" if i > 0 else "Valor")
            else:
                names.append(f"Quantidade_{i+1}" if i > 0 else "Quantidade")
        else:
            # String column - likely a category/dimension
            names.append(f"Categoria_{i+1}" if i > 0 else "Categoria")
    
    return names


def display_data(result: str | pd.DataFrame, query: str = None, force_type: str = None) -> None:
    """
    Display data with appropriate visualization.
    
    Args:
        result: Query result (string or DataFrame).
        query: SQL query used to generate result (for column naming).
        force_type: Force a specific visualization type.
    """
    # Convert to DataFrame if needed
    if isinstance(result, str):
        df = parse_query_result(result, query)
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
