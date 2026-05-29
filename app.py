import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="Finance Dashboard V2.0", layout="wide")

# =========================================================
# GOOGLE SHEETS
# =========================================================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)

sheet = client.open("Finance Dashboard DB").worksheet("transacoes")

# =========================================================
# LOAD DATA (LEDGER ONLY)
# =========================================================

def carregar_dados():
    df = pd.DataFrame(sheet.get_all_records())
    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df

df = carregar_dados()

# =========================================================
# RECURRING RULES (DERIVED FROM LEDGER)
# =========================================================

def extrair_regras_recorrentes(df):
    if df.empty:
        return pd.DataFrame()

    rules = df[df["recorrente"] == "Sim"].copy()

    # remove duplicados (mesma regra repetida no ledger)
    rules = rules.drop_duplicates(subset=["descricao", "valor", "categoria"])

    return rules

# =========================================================
# PROJEÇÃO (RUNTIME ONLY)
# =========================================================

def gerar_projecao_recorrente(rules, meses=12):
    if rules.empty:
        return pd.DataFrame()

    hoje = pd.Timestamp.today()
    datas = pd.date_range(hoje, periods=meses, freq="MS")

    rows = []

    for _, r in rules.iterrows():
        for d in datas:
            rows.append({
                "tipo": r["tipo"],
                "descricao": r["descricao"],
                "categoria": r["categoria"],
                "classificacao": r["classificacao"],
                "natureza": r["natureza"],
                "valor": float(r["valor"]),
                "data": d,
                "origem": "projecao"
            })

    return pd.DataFrame(rows)

# =========================================================
# DATASETS PRINCIPAIS
# =========================================================

rules = extrair_regras_recorrentes(df)

df_real = df.copy()
df_real["origem"] = "real"

df_forecast = gerar_projecao_recorrente(rules)

df_total = pd.concat([df_real, df_forecast], ignore_index=True)

# =========================================================
# FILTRO TEMPORAL
# =========================================================

df_real["mes_ano"] = df_real["data"].dt.to_period("M").astype(str)
df_total["mes_ano"] = df_total["data"].dt.to_period("M").astype(str)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Nova Transação")

tipo = st.sidebar.selectbox("Tipo", ["Receita", "Gasto"])

descricao = st.sidebar.text_input("Descrição")

categoria = st.sidebar.selectbox(
    "Categoria",
    ["Salário","Moradia","Alimentação","Transporte","Lazer","Investimento","Assinatura","Saúde","Educação","Outros"]
)

classificacao = st.sidebar.selectbox("Classificação", ["Essencial","Importante","Supérfluo"])

natureza = st.sidebar.selectbox("Natureza", ["Fixo","Variável"])

valor = st.sidebar.number_input("Valor", min_value=0.0, step=10.0)

data = st.sidebar.date_input("Data")

recorrente = st.sidebar.selectbox("Recorrente?", ["Não","Sim"])

# =========================================================
# ADD TRANSACTION (SÓ 1 LINHA — SEM PROJEÇÃO)
# =========================================================

if st.sidebar.button("Adicionar Transação"):

    sheet.append_row([
        len(df) + 1,
        tipo,
        descricao,
        categoria,
        classificacao,
        natureza,
        valor,
        str(data),
        recorrente,
        1,
        1
    ])

    st.success("Transação adicionada")
    st.rerun()

# =========================================================
# FILTRO
# =========================================================

meses = ["Todos"] + sorted(df_total["mes_ano"].dropna().unique(), reverse=True)

mes = st.sidebar.selectbox("Mês", meses)

if mes == "Todos":
    view = df_total
else:
    view = df_total[df_total["mes_ano"] == mes]

# =========================================================
# KPIs (REAL + PROJETADO)
# =========================================================

receitas = view[view["tipo"] == "Receita"]["valor"].sum()
gastos = view[view["tipo"] == "Gasto"]["valor"].sum()
saldo = receitas - gastos

percentual = (gastos / receitas * 100) if receitas > 0 else 0

# segurança contra progress crash
def safe(v):
    if pd.isna(v) or v == float("inf"):
        return 0
    return min(max(v, 0), 1)

# =========================================================
# UI
# =========================================================

st.title("Finance Dashboard V2.0")

col1, col2, col3 = st.columns(3)

col1.metric("Receitas", f"R$ {receitas:,.2f}")
col2.metric("Gastos", f"R$ {gastos:,.2f}")
col3.metric("Saldo", f"R$ {saldo:,.2f}")

st.progress(safe(percentual / 100))

# =========================================================
# EVOLUÇÃO
# =========================================================

st.subheader("Evolução Financeira")

evolucao = view.groupby(["mes_ano","tipo"])["valor"].sum().reset_index()

fig = px.bar(evolucao, x="mes_ano", y="valor", color="tipo", barmode="group")
st.plotly_chart(fig, use_container_width=True)

# =========================================================
# SALDO ACUMULADO (REAL ONLY)
# =========================================================

st.subheader("Saldo Acumulado (Real)")

real_monthly = df_real.groupby(["mes_ano","tipo"])["valor"].sum().unstack(fill_value=0)

real_monthly["saldo"] = real_monthly.get("Receita",0) - real_monthly.get("Gasto",0)
real_monthly["acumulado"] = real_monthly["saldo"].cumsum()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=real_monthly.index, y=real_monthly["acumulado"], mode="lines+markers"))

st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# RESERVA
# =========================================================

st.subheader("Reserva de Emergência")

gastos_fixos = df_real[
    (df_real["tipo"] == "Gasto") &
    (df_real["natureza"] == "Fixo")
]["valor"].sum()

meses_reserva = st.sidebar.slider("Meses de segurança", 3, 12, 6)

reserva_ideal = gastos_fixos * meses_reserva

patrimonio = df_real[df_real["tipo"] == "Receita"]["valor"].sum() - df_real[df_real["tipo"] == "Gasto"]["valor"].sum()

percentual_reserva = (patrimonio / reserva_ideal * 100) if reserva_ideal > 0 else 0

st.progress(safe(percentual_reserva / 100))

st.write(f"Reserva ideal: R$ {reserva_ideal:,.2f}")
st.write(f"Patrimônio real: R$ {patrimonio:,.2f}")

# =========================================================
# PROJEÇÃO (MOSTRAR DIFERENÇA)
# =========================================================

st.subheader("Visão Real vs Projetada")

view_type = st.radio("Tipo de visão", ["Real", "Projetado", "Ambos"])

if view_type == "Real":
    show = df_real
elif view_type == "Projetado":
    show = df_forecast
else:
    show = df_total

st.dataframe(show.sort_values("data", ascending=False))

# =========================================================
# ALERTAS
# =========================================================

if percentual >= 90:
    st.error("Comprometimento crítico")
elif percentual >= 70:
    st.warning("Comprometimento elevado")
else:
    st.success("Situação saudável")
