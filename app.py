# para rodar:
# streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from fpdf import FPDF

st.set_page_config(page_title="🎯 Direcionadores Estratégicos")
st.title("🎯 Direcionadores Estratégicos")

# ========= LOGIN =========
SENHA_CORRETA = "seplan123"
senha = st.text_input("🔒 Digite a senha para acessar:", type="password")
if senha != SENHA_CORRETA:
    if senha != "":
        st.error("🚫 Senha incorreta.")
    st.stop()

# ========= ARQUIVO =========
arquivo = Path("dados.xlsx")
if not arquivo.exists():
    st.error("Arquivo dados.xlsx não encontrado.")
    st.stop()

abas = pd.ExcelFile(arquivo).sheet_names

@st.cache_data
def carregar_dados(sheet):
    df = pd.read_excel(arquivo, sheet_name=sheet)
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    return df

# ========= RADAR =========
def radar_chart(df, eixo):
    if not {'populacao', 'diagnostico'}.issubset(df.columns):
        st.warning(f"A aba {eixo} não tem as colunas necessárias.")
        return None

    pop = df['populacao'].mean()
    diag = df['diagnostico'].mean()
    governo = 1

    categorias = ['Governo', 'População', 'Diagnóstico']
    valores = [governo, pop, diag]

    valores_pct = [v * 100 for v in valores]
    valores_pct.append(valores_pct[0])
    categorias_ciclo = categorias + [categorias[0]]
    pop_pct = round(valores_pct[1], 1)
    diag_pct = round(valores_pct[2], 1)
    media = round((pop_pct+diag_pct)/2)

    st.write(f"O eixo {eixo} tem **{pop_pct}%** de aderência com a população e **{diag_pct}%** com o diagnóstico técnico.")

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores_pct,
        theta=categorias_ciclo,
        fill='toself',
        name=eixo,
        text=[f"{round(v)}%" for v in valores_pct],
        hoverinfo="text+theta"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,100], tickvals=[0,25,50,75,100]),
            angularaxis=dict(direction='clockwise', rotation=90)
        ),
        showlegend=False,
        title=f"Aderência Média: {media}% - {eixo}"
    )

    return fig, pop_pct, diag_pct

# ========= CORRESPONDÊNCIA =========
def correspondencia(df, eixo):
    if not {'populacao', 'diagnostico', 'aderencia'}.issubset(df.columns):
        st.warning(f"A aba {eixo} não tem as colunas necessárias.")
        return None

    df = df.rename(columns={"populacao":"População", "diagnostico":"Diagnóstico"})
    df["Governo"] = 1
    df = df.sort_values("aderencia", ascending=False).reset_index(drop=True)

    if 'governo' in df.columns:
        rótulos_reais = df['governo'].astype(str)
    else:
        rótulos_reais = df.index.map(lambda i: f"Meta_{i+1}")

    df["governo_id"] = df.index.map(lambda i: f"id_{i+1}")
    df["nivel_aderencia"] = df["aderencia"].map({0:"Baixa",0.5:"Média",1:"Alta"})
    cores = {"Baixa":"red", "Média":"blue", "Alta":"forestgreen"}
    categorias = ["População", "Governo", "Diagnóstico"]

    dados_long = df.melt(
        id_vars=["governo_id", "nivel_aderencia"],
        value_vars=categorias,
        var_name="Eixo", value_name="Presença"
    ).query("Presença == 1")

    mapeamento = dict(zip(df["governo_id"], rótulos_reais))
    dados_long["rótulo"] = dados_long["governo_id"].map(mapeamento)

    ordem = list(dados_long["governo_id"].unique()[::-1])
    dados_long["ordem"] = pd.Categorical(dados_long["governo_id"], categories=ordem, ordered=True)

    fig = px.line(
        dados_long, x="Eixo", y="ordem", color="nivel_aderencia",
        markers=True, color_discrete_map=cores, line_group="governo_id",
        category_orders={"Eixo":categorias}, hover_data={"rótulo":True}
    )

    fig.update_traces(marker=dict(size=10, line=dict(color='black', width=1)))
    y_labels = [mapeamento[id_] for id_ in ordem]

    fig.update_layout(
        yaxis=dict(title="Metas", tickmode="array", tickvals=ordem, ticktext=y_labels),
        xaxis_title="", legend_title="Aderência",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        title=f"Correspondência - {eixo}", height=600
    )

    return fig

# ========= PDF =========
def gerar_pdf(radar_bytes, corr_bytes, aba, pop_pct, diag_pct):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0,10,txt=f"Relatório do Eixo: {aba}",ln=True,align='C')
    pdf.ln(10)
    pdf.cell(0,10,txt=f"População: {pop_pct}%",ln=True)
    pdf.cell(0,10,txt=f"Diagnóstico: {diag_pct}%",ln=True)
    pdf.ln(10)

    pdf.cell(0,10,"Radar Chart",ln=True)
    radar_path = f"radar_temp_{aba}.png"
    with open(radar_path,"wb") as f:
        f.write(radar_bytes)
    pdf.image(radar_path,w=150)
    pdf.ln(10)

    pdf.cell(0,10,"Gráfico de Correspondência",ln=True)
    corr_path = f"corr_temp_{aba}.png"
    with open(corr_path,"wb") as f:
        f.write(corr_bytes)
    pdf.image(corr_path,w=150)

    return pdf.output(dest='S').encode('latin1')

# ========= INTERFACE =========
abas_escolhidas = st.multiselect("Escolha 1 ou mais eixos:", abas)

for aba in abas_escolhidas:
    st.markdown(f"## 📊 Eixo: {aba}")
    df = carregar_dados(aba)

    # RADAR
    st.subheader(f"Radar Chart - {aba}")
    radar_result = radar_chart(df, aba)
    if radar_result:
        fig_radar, pop_pct, diag_pct = radar_result
        st.plotly_chart(fig_radar, use_container_width=True)

        radar_png = fig_radar.to_image(format="png")
        st.download_button(
            label=f"📥 Baixar Radar Chart ({aba})",
            data=radar_png,
            file_name=f"radar_{aba}.png",
            mime="image/png"
        )

    # CORRESPONDÊNCIA
    st.subheader(f"Correspondência - {aba}")
    fig_corr = correspondencia(df, aba)
    if fig_corr:
        st.plotly_chart(fig_corr, use_container_width=True)

        corr_png = fig_corr.to_image(format="png")
        st.download_button(
            label=f"📥 Baixar Correspondência ({aba})",
            data=corr_png,
            file_name=f"correspondencia_{aba}.png",
            mime="image/png"
        )

    # PDF
    if radar_result and fig_corr:
        pdf_bytes = gerar_pdf(radar_png, corr_png, aba, pop_pct, diag_pct)
        st.download_button(
            label=f"📄 Baixar Relatório ({aba}) em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_{aba}.pdf",
            mime="application/pdf"
        )
