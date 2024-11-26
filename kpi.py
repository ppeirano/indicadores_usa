import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# Configuración inicial
st.set_page_config(layout="wide", page_title="Indicadores Económicos de EE. UU.")

# Barra lateral para configuración
st.sidebar.header("Configuración")
today = datetime.today()
one_year_ago = today - timedelta(days=365)

start_date = st.sidebar.date_input("Selecciona la fecha de inicio", one_year_ago)
end_date = st.sidebar.date_input("Selecciona la fecha de fin", today)

if start_date > end_date:
    st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")

# Clave de la API de FRED
API_KEY = "f5c520998557f7aec96adf6284098978"

# Función para obtener datos desde FRED
def get_fred_data(series_id, api_key, start_date, end_date):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        observations = data.get("observations", [])
        df = pd.DataFrame({
            "Fecha": [obs["date"] for obs in observations],
            "Valor": [
                float(obs["value"]) if obs["value"].replace('.', '', 1).isdigit() else None
                for obs in observations
            ]
        }).dropna()  # Elimina filas con valores no válidos
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df["Variación Mensual (%)"] = df["Valor"].pct_change() * 100
        return df
    else:
        st.error(f"Error al obtener datos para {series_id}. Código de estado: {response.status_code}")
        return pd.DataFrame(columns=["Fecha", "Valor", "Variación Mensual (%)"])

# Mapeo de indicadores a series de FRED
indicator_map = {
    "Curva de tasas (todos los periodos)": {
        "1 mes": "DGS1MO",
        "3 meses": "DGS3MO",
        "6 meses": "DGS6MO",
        "1 año": "DGS1",
        "2 años": "DGS2",
        "3 años": "DGS3",
        "5 años": "DGS5",
        "7 años": "DGS7",
        "10 años": "DGS10",
        "20 años": "DGS20",
        "30 años": "DGS30",
    },
    "Tasa de la Fed": "FEDFUNDS",
    "Nivel de actividad (PIB)": "GDPC1",
    "Empleo (Tasa de Desempleo)": "UNRATE",
    "Inflación (IPC)": "CPIAUCSL",
}

# Series de tasas breakeven para 2 y 10 años
breakeven_series = {
    "Breakeven 2 años": "T5YIE",
    "Breakeven 10 años": "T10YIE",
}

# Selección de indicadores en la barra lateral
indicators = list(indicator_map.keys())
selected_indicators = st.sidebar.multiselect("Selecciona los indicadores a visualizar", indicators, default=indicators)

# Visualización de datos
for indicator in selected_indicators:
    if indicator == "Curva de tasas (todos los periodos)":
        #st.header("Curva de Tasas")
        yield_curve_data = pd.DataFrame()
        for period, series_id in indicator_map[indicator].items():
            data = get_fred_data(series_id, API_KEY, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            if not data.empty:
                data = data[["Fecha", "Valor"]].rename(columns={"Valor": period})
                data.set_index("Fecha", inplace=True)
                if yield_curve_data.empty:
                    yield_curve_data = data
                else:
                    yield_curve_data = yield_curve_data.join(data, how="outer")

        if not yield_curve_data.empty:
            fig_yield_curve = go.Figure()
            for period in yield_curve_data.columns:
                fig_yield_curve.add_trace(
                    go.Scatter(
                        x=yield_curve_data.index,
                        y=yield_curve_data[period],
                        mode="lines",
                        name=period
                    )
                )
            fig_yield_curve.update_layout(
                title="Curva de Tasas - Todos los Periodos",
                xaxis_title="Fecha",
                yaxis_title="Tasa (%)",
                legend_title="Período",
                hovermode="x unified",
                template="plotly_white",
            )
            st.plotly_chart(fig_yield_curve, use_container_width=True)

            # Tasas breakeven
            #st.header("Tasas Breakeven")
            breakeven_data = pd.DataFrame()
            for label, series_id in breakeven_series.items():
                data = get_fred_data(series_id, API_KEY, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                if not data.empty:
                    data = data[["Fecha", "Valor"]].rename(columns={"Valor": label})
                    data.set_index("Fecha", inplace=True)
                    if breakeven_data.empty:
                        breakeven_data = data
                    else:
                        breakeven_data = breakeven_data.join(data, how="outer")

            if not breakeven_data.empty:
                fig_breakeven = go.Figure()
                for label in breakeven_data.columns:
                    fig_breakeven.add_trace(
                        go.Scatter(
                            x=breakeven_data.index,
                            y=breakeven_data[label],
                            mode="lines",
                            name=label,
                        )
                    )
                fig_breakeven.update_layout(
                    title="Tasas Breakeven - 2 y 10 Años",
                    xaxis_title="Fecha",
                    yaxis_title="Tasa (%)",
                    legend_title="Tipo",
                    hovermode="x unified",
                    template="plotly_white",
                )
                st.plotly_chart(fig_breakeven, use_container_width=True)

                # Gráfico de diferencia (10 años - 2 años)
                #st.header("Diferencia: 10 Años - 2 Años")
                if "Breakeven 10 años" in breakeven_data and "Breakeven 2 años" in breakeven_data:
                    breakeven_data["Diferencia"] = breakeven_data["Breakeven 10 años"] - breakeven_data["Breakeven 2 años"]
                    fig_difference = go.Figure()
                    fig_difference.add_trace(
                        go.Scatter(
                            x=breakeven_data.index,
                            y=breakeven_data["Diferencia"],
                            mode="lines",
                            name="Diferencia (10 años - 2 años)",
                            line=dict(color="red", width=2)
                        )
                    )
                    fig_difference.update_layout(
                        title="Diferencia: Tasa a 10 Años - Tasa a 2 Años",
                        xaxis_title="Fecha",
                        yaxis_title="Diferencia (%)",
                        hovermode="x unified",
                        template="plotly_white",
                    )
                    st.plotly_chart(fig_difference, use_container_width=True)
                else:
                    st.warning("No se encontraron datos suficientes para calcular la diferencia entre 10 años y 2 años.")
            else:
                st.warning("No se encontraron datos para las tasas breakeven en el rango de fechas seleccionado.")
        else:
            st.warning("No se encontraron datos para la curva de tasas en el rango de fechas seleccionado.")
    else:
        #st.header(indicator)
        series_id = indicator_map[indicator]
        data = get_fred_data(series_id, API_KEY, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        if not data.empty:
            fig = go.Figure()
            # Línea para valores absolutos
            fig.add_trace(
                go.Scatter(
                    x=data["Fecha"],
                    y=data["Valor"],
                    mode="lines",
                    name=f"{indicator} (Valor Absoluto)",
                    line=dict(width=2),
                )
            )
            # Barras para variación mensual
            fig.add_trace(
                go.Bar(
                    x=data["Fecha"],
                    y=data["Variación Mensual (%)"],
                    name="Variación Mensual (%)",
                    marker_color="orange",
                    opacity=0.6,
                    yaxis="y2",
                )
            )
            # Configuración de ejes
            fig.update_layout(
                title=f"{indicator} entre {start_date} y {end_date}",
                xaxis=dict(title="Fecha"),
                yaxis=dict(title="Valor Absoluto"),
                yaxis2=dict(
                    title="Variación Mensual (%)",
                    overlaying="y",
                    side="right",
                ),
                legend=dict(x=0.01, y=0.99),
                hovermode="x unified",
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No se encontraron datos para {indicator} en el rango de fechas seleccionado.")

# Nota final
st.sidebar.info("Los datos son obtenidos en tiempo real desde la API de FRED.")
