import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Finance Dashboard V0",
    layout="wide"
)

# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect(
    "database.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    descricao TEXT,
    categoria TEXT,
    classificacao TEXT,
    natureza TEXT,
    valor REAL,
    data TEXT,
    recorrente TEXT,
    parcela_atual INTEGER,
    total_parcelas INTEGER
)
""")

conn.commit()

# =========================================================
# FUNÇÕES
# =========================================================

def adicionar_transacao(
    tipo,
    descricao,
    categoria,
    classificacao,
    natureza,
    valor,
    data,
    recorrente,
    total_parcelas
):

    data_base = pd.to_datetime(data)

    quantidade_meses = 1

    # -----------------------------------------------------

    if recorrente == "Sim":
        quantidade_meses = 12

    quantidade_final = max(
        quantidade_meses,
        total_parcelas
    )

    # -----------------------------------------------------

    for parcela in range(quantidade_final):

        data_parcela = (
            data_base
            + pd.DateOffset(months=parcela)
        )

        descricao_final = descricao

        if total_parcelas > 1:

            descricao_final = (
                f"{descricao} "
                f"({parcela + 1}/{total_parcelas})"
            )

        cursor.execute("""
        INSERT INTO transacoes (
            tipo,
            descricao,
            categoria,
            classificacao,
            natureza,
            valor,
            data,
            recorrente,
            parcela_atual,
            total_parcelas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tipo,
            descricao_final,
            categoria,
            classificacao,
            natureza,
            valor,
            str(data_parcela.date()),
            recorrente,
            parcela + 1,
            total_parcelas
        ))

    conn.commit()

# ---------------------------------------------------------

def carregar_dados():

    return pd.read_sql(
        "SELECT * FROM transacoes",
        conn
    )

# ---------------------------------------------------------

def excluir_transacao(id_transacao):

    cursor.execute(
        "DELETE FROM transacoes WHERE id = ?",
        (id_transacao,)
    )

    conn.commit()

# ---------------------------------------------------------

def atualizar_transacao(
    id_transacao,
    descricao,
    categoria,
    classificacao,
    natureza,
    valor
):

    cursor.execute("""
    UPDATE transacoes
    SET
        descricao = ?,
        categoria = ?,
        classificacao = ?,
        natureza = ?,
        valor = ?
    WHERE id = ?
    """, (
        descricao,
        categoria,
        classificacao,
        natureza,
        valor,
        id_transacao
    ))

    conn.commit()

# =========================================================
# CARREGAR DADOS
# =========================================================

df = carregar_dados()

# =========================================================
# DATAS
# =========================================================

if not df.empty:

    df["data"] = pd.to_datetime(
        df["data"]
    )

    df["mes"] = df["data"].dt.month

    df["ano"] = df["data"].dt.year

    meses_nomes = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    }

    df["mes_nome"] = (
        df["mes"].map(meses_nomes)
    )

    df["mes_ano"] = (
        df["mes_nome"]
        + "/"
        + df["ano"].astype(str)
    )

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "Nova Transação"
)

tipo = st.sidebar.selectbox(
    "Tipo",
    ["Receita", "Gasto"]
)

desricao = st.sidebar.text_input(
    "Descrição"
)

categoria = st.sidebar.selectbox(
    "Categoria",
    [
        "Salário",
        "Moradia",
        "Alimentação",
        "Transporte",
        "Lazer",
        "Investimento",
        "Assinatura",
        "Saúde",
        "Educação",
        "Outros"
    ]
)

classificacao = st.sidebar.selectbox(
    "Classificação",
    [
        "Essencial",
        "Importante",
        "Supérfluo"
    ]
)

# =========================================================
# FIXO VS VARIÁVEL
# =========================================================

natureza = st.sidebar.selectbox(
    "Natureza",
    [
        "Fixo",
        "Variável"
    ]
)

valor = st.sidebar.number_input(
    "Valor",
    min_value=0.0,
    step=10.0
)

data = st.sidebar.date_input(
    "Data"
)

recorrente = st.sidebar.selectbox(
    "Recorrente?",
    ["Não", "Sim"]
)

parcelado = st.sidebar.selectbox(
    "Parcelado?",
    ["Não", "Sim"]
)

total_parcelas = 1

if parcelado == "Sim":

    total_parcelas = st.sidebar.number_input(
        "Quantidade de Parcelas",
        min_value=2,
        max_value=60,
        step=1
    )

# =========================================================
# BOTÃO
# =========================================================

if st.sidebar.button(
    "Adicionar Transação"
):

    adicionar_transacao(
        tipo,
        descricao,
        categoria,
        classificacao,
        natureza,
        valor,
        str(data),
        recorrente,
        total_parcelas
    )

    st.sidebar.success(
        "Transação adicionada!"
    )

    st.rerun()

# =========================================================
# FILTROS AVANÇADOS
# =========================================================

st.sidebar.subheader(
    "Filtros Avançados"
)

if df.empty:
    st.warning("Adicione transações para usar os filtros avançados.")
    # Initialize df_filtrado as an empty DataFrame with the expected columns
    # to prevent KeyErrors later in the script when trying to access its columns.
    df_filtrado = pd.DataFrame(columns=[
        'id', 'tipo', 'descricao', 'categoria', 'classificacao', 'natureza',
        'valor', 'data', 'recorrente', 'parcela_atual', 'total_parcelas',
        'mes', 'ano', 'mes_nome', 'mes_ano'
    ])
    # No need to st.stop() here, as we want the app to render with empty data.
    # The previous st.stop() was causing issues in bare mode and was not preventing
    # further execution in the intended way.
else:
    meses_disponiveis = sorted(
        df["mes_ano"].unique(),
        reverse=True
    )

    mes_selecionado = st.sidebar.selectbox(
        "Mês",
        meses_disponiveis
    )

    tipo_filtro = st.sidebar.multiselect(
        "Tipo",
        df["tipo"].unique(),
        default=df["tipo"].unique()
    )

    categoria_filtro = st.sidebar.multiselect(
        "Categoria",
        df["categoria"].unique(),
        default=df["categoria"].unique()
    )

    classificacao_filtro = st.sidebar.multiselect(
        "Classificação",
        df["classificacao"].unique(),
        default=df["classificacao"].unique()
    )

    natureza_filtro = st.sidebar.multiselect(
        "Natureza",
        df["natureza"].unique(),
        default=df["natureza"].unique()
    )

# =========================================================
# RESETAR BANCO
# =========================================================

st.sidebar.divider()

st.sidebar.subheader(
    "Administração"
)

if st.sidebar.button(
    "Resetar Todas as Transações"
):

    cursor.execute(
        "DELETE FROM transacoes"
    )

    cursor.execute("""
    DELETE FROM sqlite_sequence
    WHERE name='transacoes'
    """)

    conn.commit()

    st.sidebar.success(
        "Banco resetado com sucesso!"
    )

    st.rerun()
    
    # ---------------------------------------------------------

    df_filtrado = df[
        (df["mes_ano"] == mes_selecionado)
        &
        (df["tipo"].isin(tipo_filtro))
        &
        (df["categoria"].isin(categoria_filtro))
        &
        (df["classificacao"].isin(classificacao_filtro))
        &
        (df["natureza"].isin(natureza_filtro))
    ]

# =========================================================
# MÉTRICAS
# =========================================================

# Initialize metrics with default values (0) if df_filtrado is empty
receitas = 0.0
gastos = 0.0
saldo = 0.0
percentual = 0.0
margem_seguranca = 0.0
saldo_livre_real = 0.0
media_receitas = 0.0
media_gastos = 0.0
tendencia_gastos = 0.0
reserva_ideal = 0.0
saldo_acumulado_total = 0.0
percentual_reserva = 0.0
investimentos = 0.0

if not df_filtrado.empty:
    receitas = df_filtrado[
        df_filtrado["tipo"] == "Receita"
    ]["valor"].sum()

    gastos = df_filtrado[
        df_filtrado["tipo"] == "Gasto"
    ]["valor"].sum()

    saldo = receitas - gastos

    if receitas > 0:

        percentual = (
            gastos / receitas
        ) * 100

    # =========================================================
    # SALDO LIVRE REAL
    # =========================================================

    margem_seguranca = receitas * 0.10

    saldo_livre_real = (
        saldo - margem_seguranca
    )

    # =========================================================
    # MÉDIAS MENSAIS
    # =========================================================
    # These calculations should ideally use the full df, not df_filtrado
    # unless the intention is to show averages for the selected month.
    # Assuming full df for overall averages
    if not df.empty:
        media_receitas = (
            df[df["tipo"] == "Receita"]
            .groupby("mes_ano")["valor"]
            .sum()
            .mean()
        )

        media_gastos = (
            df[df["tipo"] == "Gasto"]
            .groupby("mes_ano")["valor"]
            .sum()
            .mean()
        )

    # =========================================================
    # TENDÊNCIA
    # =========================================================

    hoje = datetime.now().day

    dias_mes = 30

    fator = dias_mes / max(hoje, 1)

    tendencia_gastos = (
        gastos * fator
    )

    # =========================================================
    # RESERVA DE EMERGÊNCIA
    # =========================================================

    # Assuming these calculations should use the full df, not df_filtrado
    if not df.empty:
        gastos_fixos = df[
            (df["natureza"] == "Fixo")
            &
            (df["tipo"] == "Gasto")
        ]["valor"].sum()

        # Months reserve will be from sidebar, initialized to a default if df is empty
        meses_reserva = st.sidebar.slider(
            "Meses de segurança",
            3,
            12,
            6,
            key="meses_reserva_main"
        )

        reserva_ideal = (
            gastos_fixos * meses_reserva
        )

        saldo_acumulado_total = (
            df[df["tipo"] == "Receita"]["valor"].sum()
            -
            df[df["tipo"] == "Gasto"]["valor"].sum()
        )

        if reserva_ideal > 0:

            percentual_reserva = (
                saldo_acumulado_total
                / reserva_ideal
            ) * 100

    # =========================================================
    # INVESTIMENTOS
    # =========================================================

    investimentos = df_filtrado[
        df_filtrado["categoria"] == "Investimento"
    ]["valor"].sum()

# =========================================================
# KPIs
# =========================================================

st.title(
    "Finance Dashboard V0"
)

# Display current month if df is not empty, otherwise a placeholder
current_month_display = mes_selecionado if not df.empty else "N/A"
st.subheader(
    f"Visão Mensal: {current_month_display}"
)

# ---------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Receitas",
    f"R$ {receitas:,.2f}"
)

col2.metric(
    "Gastos",
    f"R$ {gastos:,.2f}"
)

col3.metric(
    "Saldo",
    f"R$ {saldo:,.2f}"
)

col4.metric(
    "Saldo Livre Real",
    f"R$ {saldo_livre_real:,.2f}"
)

# ---------------------------------------------------------

col5, col6, col7, col8 = st.columns(4)

col5.metric(
    "% Comprometido",
    f"{percentual:.1f}%"
)

col6.metric(
    "Tendência do Mês",
    f"R$ {tendencia_gastos:,.2f}"
)

col7.metric(
    "Investimentos",
    f"R$ {investimentos:,.2f}"
)

col8.metric(
    "Reserva Atual",
    f"{percentual_reserva:.1f}%"
)

# =========================================================
# ALERTAS
# =========================================================

if percentual >= 90:

    st.error(
        "Comprometimento crítico."
    )

elif percentual >= 70:

    st.warning(
        "Comprometimento elevado."
    )

else:

    st.success(
        "Situação saudável."
    )

# =========================================================
# FIXO VS VARIÁVEL
# =========================================================

st.subheader(
    "Fixos vs Variáveis"
)

natureza_df = (
    df_filtrado[
        df_filtrado["tipo"] == "Gasto"
    ]
    .groupby("natureza")["valor"]
    .sum()
    .reset_index()
)

if not natureza_df.empty:

    fig_natureza = px.pie(
        natureza_df,
        values="valor",
        names="natureza"
    )

    st.plotly_chart(
        fig_natureza,
        use_container_width=True
    )
else:
    st.info("Nenhum gasto para mostrar na categorização de Natureza.")

# =========================================================
# CLASSIFICAÇÃO
# =========================================================

st.subheader(
    "Classificação dos Gastos"
)

classificacao_df = (
    df_filtrado[
        df_filtrado["tipo"] == "Gasto"
    ]
    .groupby("classificacao")["valor"]
    .sum()
    .reset_index()
)

if not classificacao_df.empty:

    fig_class = px.pie(
        classificacao_df,
        values="valor",
        names="classificacao"
    )

    st.plotly_chart(
        fig_class,
        use_container_width=True
    )
else:
    st.info("Nenhum gasto para mostrar na Classificação.")

# =========================================================
# EVOLUÇÃO FINANCEIRA
# =========================================================

st.subheader(
    "Evolução Financeira"
)

if not df.empty:
    evolucao = (
        df.groupby(
            ["mes_ano", "tipo"]
        )["valor"]
        .sum()
        .reset_index()
    )

    fig_bar = px.bar(
        evolucao,
        x="mes_ano",
        y="valor",
        color="tipo",
        barmode="group"
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True
    )
else:
    st.info("Adicione transações para ver a Evolução Financeira.")

# =========================================================
# SALDO ACUMULADO
# =========================================================

st.subheader(
    "Saldo Acumulado"
)

if not df.empty:
    saldo_mensal = (
        df.groupby(
            ["mes_ano", "tipo"]
        )["valor"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    if "Receita" not in saldo_mensal.columns:
        saldo_mensal["Receita"] = 0

    if "Gasto" not in saldo_mensal.columns:
        saldo_mensal["Gasto"] = 0

    saldo_mensal["saldo_mes"] = (
        saldo_mensal["Receita"]
        - saldo_mensal["Gasto"]
    )

    saldo_mensal["saldo_acumulado"] = (
        saldo_mensal["saldo_mes"]
        .cumsum()
    )

    fig_acumulado = go.Figure()

    fig_acumulado.add_trace(
        go.Scatter(
            x=saldo_mensal["mes_ano"],
            y=saldo_mensal["saldo_acumulado"],
            mode="lines+markers"
        )
    )

    st.plotly_chart(
        fig_acumulado,
        use_container_width=True
    )
else:
    st.info("Adicione transações para ver o Saldo Acumulado.")

# =========================================================
# RESERVA DE EMERGÊNCIA
# =========================================================

st.subheader(
    "Reserva de Emergência"
)

# Default value for months_reserva if df is empty
if df.empty:
    meses_reserva_display = 6
else:
    meses_reserva_display = st.sidebar.slider(
        "Meses de segurança",
        3,
        12,
        6,
        key="meses_reserva_display_bottom"
    )

st.progress(
    min(
        percentual_reserva / 100,
        1.0
    )
)

st.write(
    f"""
    Reserva ideal:
    R$ {reserva_ideal:,.2f}
    """
)

st.write(
    f"""
    Patrimônio atual:
    R$ {saldo_acumulado_total:,.2f}
    """
)

# =========================================================
# METAS
# =========================================================

st.subheader(
    "Metas Financeiras"
)

meta_nome = st.text_input(
    "Nome da Meta"
)

meta_valor = st.number_input(
    "Valor da Meta",
    min_value=0.0,
    step=100.0
)

if meta_valor > 0:

    progresso_meta = (
        saldo_acumulado_total
        / meta_valor
    ) * 100

    st.progress(
        min(
            progresso_meta / 100,
            1.0
        )
    )

    st.write(
        f"""
        Progresso:
        {progresso_meta:.1f}%
        """
    )

# =========================================================
# MÉDIAS MENSAIS
# =========================================================

st.subheader(
    "Médias Mensais"
)

media1, media2 = st.columns(2)

media1.metric(
    "Média Receitas",
    f"R$ {media_receitas:,.2f}"
)

media2.metric(
    "Média Gastos",
    f"R$ {media_gastos:,.2f}"
)

# =========================================================
# SIMULADOR
# =========================================================

st.subheader(
    "Simulador de Compra"
)

with st.expander(
    "Abrir Simulador"
):

    valor_compra = st.number_input(
        "Valor da Parcela",
        min_value=0.0,
        step=10.0,
        key="valor_compra"
    )

    parcelas_compra = st.number_input(
        "Parcelas",
        min_value=1,
        max_value=60,
        step=1,
        key="parcelas_compra"
    )

    impacto = (
        valor_compra / receitas * 100
        if receitas > 0 else 0
    )

    saldo_pos_compra = (
        saldo_livre_real
        - valor_compra
    )

    st.write(
        f"""
        Impacto:
        {impacto:.1f}% da renda
        """
    )

    st.write(
        f"""
        Saldo restante:
        R$ {saldo_pos_compra:,.2f}
        """
    )

    if saldo_pos_compra < 0:

        st.error(
            "Compra não recomendada."
        )

    else:

        st.success(
            "Compra segura."
        )

# =========================================================
# EDITAR / EXCLUIR
# =========================================================

st.subheader(
    "Editar / Excluir"
)

if not df_filtrado.empty:

    transacao_id = st.selectbox(
        "Selecione a transação",
        df_filtrado["id"]
    )

    transacao = df_filtrado[
        df_filtrado["id"] == transacao_id
    ].iloc[0]

    nova_descricao = st.text_input(
        "Nova descrição",
        transacao["descricao"]
    )

    nova_categoria = st.selectbox(
        "Nova categoria",
        [
            "Salário",
            "Moradia",
            "Alimentação",
            "Transporte",
            "Lazer",
            "Investimento",
            "Assinatura",
            "Saúde",
            "Educação",
            "Outros"
        ],
        index = [
            "Salário",
            "Moradia",
            "Alimentação",
            "Transporte",
            "Lazer",
            "Investimento",
            "Assinatura",
            "Saúde",
            "Educação",
            "Outros"
        ].index(transacao["categoria"])
    )

    nova_classificacao = st.selectbox(
        "Nova classificação",
        [
            "Essencial",
            "Importante",
            "Supérfluo"
        ],
        index = [
            "Essencial",
            "Importante",
            "Supérfluo"
        ].index(transacao["classificacao"])
    )

    nova_natureza = st.selectbox(
        "Nova natureza",
        [
            "Fixo",
            "Variável"
        ],
        index = [
            "Fixo",
            "Variável"
        ].index(transacao["natureza"])
    )

    novo_valor = st.number_input(
        "Novo valor",
        value=float(transacao["valor"])
    )

    col_edit, col_delete = st.columns(2)

    # -----------------------------------------------------

    with col_edit:

        if st.button(
            "Salvar Alterações"
        ):

            atualizar_transacao(
                transacao_id,
                nova_descricao,
                nova_categoria,
                nova_classificacao,
                nova_natureza,
                novo_valor
            )

            st.success(
                "Atualizado."
            )

            st.rerun()

    # -----------------------------------------------------

    with col_delete:

        if st.button(
            "Excluir"
        ):

            excluir_transacao(
                transacao_id
            )

            st.warning(
                "Transação excluída."
            )

            st.rerun()

else:
    st.info("Nenhuma transação para editar ou excluir.")

# =========================================================
# TABELA FINAL
# =========================================================

st.subheader(
    "Transações"
)

if not df_filtrado.empty:
    st.dataframe(
        df_filtrado.sort_values(
            by="data",
            ascending=False
        )
    )
else:
    st.info("Nenhuma transação para exibir.")
