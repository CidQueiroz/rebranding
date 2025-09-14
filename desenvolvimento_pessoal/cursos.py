import streamlit as st
import pandas as pd
from sheets import autenticar_gspread
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe

SHEET_NAME = "RPD"
WORKSHEET_CURSOS = "Cursos"


@st.cache_data(ttl=60)
def ler_cursos_sheets():
    """
    Lê os dados da planilha 'Cursos' e os retorna como um DataFrame.
    Aplica cache para evitar leituras repetidas.
    """
    try:
        client = autenticar_gspread()
        sheet = client.open(SHEET_NAME)
        worksheet = sheet.worksheet(WORKSHEET_CURSOS)
        df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
        df = df.dropna(how="all")

        # Garante que a coluna de percentual seja numérica
        if not df.empty:
            df['Percentual'] = pd.to_numeric(df['Percentual'], errors='coerce').fillna(0).astype(int)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"A planilha '{WORKSHEET_CURSOS}' não foi encontrada. Por favor, crie-a.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao ler a planilha de cursos: {e}")
        return pd.DataFrame()


def atualizar_progresso_sheets(nome_curso, novo_percentual):
    """
    Atualiza o percentual de um curso específico na planilha.
    """
    try:
        client = autenticar_gspread()
        sheet = client.open(SHEET_NAME)
        worksheet = sheet.worksheet(WORKSHEET_CURSOS)
        df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)

        # Encontra a linha correspondente ao curso e atualiza o percentual
        if nome_curso in df['Nome do curso'].values:
            df.loc[df['Nome do curso'] == nome_curso, 'Percentual'] = novo_percentual
            set_with_dataframe(worksheet, df)
            st.toast(f"Progresso de '{nome_curso}' salvo!", icon="✅")
        else:
            st.warning(f"Curso '{nome_curso}' não encontrado para atualização.")

    except Exception as e:
        st.error(f"Erro ao atualizar o progresso: {e}")


def exibir_painel_cursos():
    """
    Renderiza a página do Painel de Controle de Cursos com dados do Google Sheets.
    """
    st.title("Painel de Controle de Treinamento")
    st.markdown("O mapa estratégico da sua evolução. Monitore seu progresso e mantenha o foco na missão atual.")

    df_cursos = ler_cursos_sheets()

    if df_cursos.empty:
        st.info("Nenhum curso encontrado na planilha 'Cursos'.")
        return

    fases = df_cursos['Fase do curso'].unique()
    
    cursos_concluidos = 0
    total_cursos = len(df_cursos)

    for fase in fases:
        with st.expander(f"**Fase {int(fase)}**"):
            cursos_na_fase = df_cursos[df_cursos['Fase do curso'] == fase]
            
            for _, curso_row in cursos_na_fase.iterrows():
                nome_curso = curso_row['Nome do curso']
                motivacao = curso_row['Motivação']
                prazo = curso_row['Prazo conclusão']
                percentual_atual = int(curso_row['Percentual'])

                st.subheader(nome_curso)
                st.caption(f"Motivação: {motivacao} | Prazo: {prazo}")

                # Layout em colunas para o slider e o status
                col1, col2 = st.columns([3, 1])

                with col1:
                    novo_percentual = st.slider(
                        label="Progresso",
                        min_value=0,
                        max_value=100,
                        value=percentual_atual,
                        step=5,
                        key=f"slider_{nome_curso}"
                    )
                    # Se o valor do slider mudou, salva o novo progresso
                    if novo_percentual != percentual_atual:
                        atualizar_progresso_sheets(nome_curso, novo_percentual)
                        # Força o rerender para mostrar o valor atualizado imediatamente
                        st.rerun()

                with col2:
                    if percentual_atual == 100:
                        st.success("✅ Concluído")
                        cursos_concluidos += 1
                    else:
                        st.info(f"{percentual_atual}%")
            
            st.write("---")

    st.divider()

    # --- BARRA DE PROGRESSO GERAL ---
    st.header("Progresso Geral da Campanha de Rebranding")
    if total_cursos > 0:
        percentual_geral = (cursos_concluidos / total_cursos) * 100
        st.progress(int(percentual_geral), text=f"{percentual_geral:.1f}% Concluído")
    else:
        st.info("Nenhum curso catalogado para calcular o progresso geral.")