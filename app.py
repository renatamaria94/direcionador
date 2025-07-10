# para rodar:
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

    # usa a coluna \"governo\" como rótulo
    rótulos_reais = df['governo'].astype(str)

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

    y_labels = [mapeamento[id_] for id_ in ordem]

    # calcula altura dinâmica: 30px por linha, mínimo 400
    altura = max(400, len(ordem) * 30)
    def lista_formatada(lista):
        if len(lista) == 0:
            return ""
        if len(lista) == 1:
            return lista[0]
        return ', '.join(lista[:-1]) + ' e ' + lista[-1]


    # prepara as listas por nível de aderência
    altas = df.loc[df['nivel_aderencia'] == 'Alta', 'governo'].astype(str).tolist()
    medias = df.loc[df['nivel_aderencia'] == 'Média', 'governo'].astype(str).tolist()
    baixas = df.loc[df['nivel_aderencia'] == 'Baixa', 'governo'].astype(str).tolist()
    # inicializa as strings
    texto_altas = ""
    texto_medias = ""
    texto_baixas = ""

    if altas:
        texto_altas = f"As metas com **alta aderência** são: {lista_formatada(altas)}."
    if medias:
        texto_medias = f"As metas com **média aderência** são: {lista_formatada(medias)}."
    if baixas:
        texto_baixas = f"As metas com **baixa aderência** são: {lista_formatada(baixas)}."

    if texto_altas:
        st.success(texto_altas)
    if texto_medias:
        st.info(texto_medias)
    if texto_baixas:
        st.error(texto_baixas)




    fig.update_layout(
        yaxis=dict(title="Metas", tickmode="array", tickvals=ordem, ticktext=y_labels),
        xaxis_title="", legend_title="Aderência",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        title=f"Correspondência - {eixo}",
        height=altura
    )
# Metas vai ser Ações compactuadas
    return fig


# ========= PDF =========
def gerar_pdf(aba, pop_pct, diag_pct):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0,10,txt=f"Relatório do Eixo: {aba}",ln=True,align='C')
    pdf.ln(10)
    pdf.cell(0,10,txt=f"População: {pop_pct}%",ln=True)
    pdf.cell(0,10,txt=f"Diagnóstico: {diag_pct}%",ln=True)
    pdf.ln(10)

    pdf.cell(0,10,"Os gráficos interativos estão disponíveis na aplicação.",ln=True)

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

    # CORRESPONDÊNCIA
    st.subheader(f"Correspondência - {aba}")
    fig_corr = correspondencia(df, aba)
    if fig_corr:
        st.plotly_chart(fig_corr, use_container_width=True)

    # PDF
    #if radar_result and fig_corr:
    #    pdf_bytes = gerar_pdf(aba, pop_pct, diag_pct)
    #    st.download_button(
    #        label=f"📄 Baixar Relatório ({aba}) em PDF",
    #        data=pdf_bytes,
    #        file_name=f"relatorio_{aba}.pdf",
    #        mime="application/pdf"
    #    )

