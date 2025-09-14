import streamlit as st
import pandas as pd
from datetime import datetime
import pytz, gspread, rebranding, protocolo_diario
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from auth import autenticar_usuario, adicionar_usuario
from estoque import ler_estoque_sheets, adicionar_item_estoque, registrar_venda_sheets, atualizar_estoque_sheets
from sheets import autenticar_gspread, salvar_resposta_sheets, ler_respostas_sheets
from desenvolvimento_pessoal import cursos

# Nome da planilha e aba
SHEET_NAME = "RPD"
WORKSHEET_NAME = "Respostas"
WORKSHEET_ESTOQUE = "Estoque"
WORKSHEET_VENDAS = "Vendas"

GOOGLE_ANALYTICS = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-PJG10ZYPBS"></script>
                    <script>
                        window.dataLayer = window.dataLayer || [];
                        function gtag(){dataLayer.push(arguments);}
                        gtag('js', new Date());

                        gtag('config', 'G-PJG10ZYPBS');
                    </script>"""
st.html(GOOGLE_ANALYTICS)

# Configuração inicial do Streamlit
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False
    st.session_state.nome_usuario = ""
    st.session_state.usuario_logado = ""
if "mostrar_cadastro" not in st.session_state:
    st.session_state.mostrar_cadastro = False

if not st.session_state.usuario_autenticado:
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar_usuario(usuario, senha):
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    st.markdown("---")
    st.subheader("Novo por aqui? Cadastre-se!")

    if st.button("Adicionar usuário"):
        st.session_state.mostrar_cadastro = True

    if st.session_state.get("mostrar_cadastro", False):
        with st.form("form_cadastro"):
            novo_nome = st.text_input("Nome completo")
            novo_usuario = st.text_input("Novo usuário")
            nova_senha = st.text_input("Nova senha", type="password")
            cadastrar = st.form_submit_button("Cadastrar")
            if cadastrar:
                if adicionar_usuario(novo_nome, novo_usuario, nova_senha):
                    st.success("Usuário cadastrado com sucesso! Faça login.")
                    st.session_state.mostrar_cadastro = False
                else:
                    st.error("Erro ao cadastrar usuário. Tente outro nome de usuário.")
    st.stop()

st.sidebar.write(f"Usuário: {st.session_state.nome_usuario}")
if st.sidebar.button("Sair"):
    st.session_state.usuario_autenticado = False
    st.session_state.nome_usuario = ""
    st.session_state.usuario_logado = ""
    st.rerun()

# Menu lateral
st.sidebar.title("Menu")
opcoes_menu = ["Responder perguntas", "Visualizar respostas"]

if st.session_state.get("usuario_logado") in ['cid', 'Cid', 'Cleo', 'cleo', 'quiopa', 'zanah']:

    usuario_logado = st.session_state.get("usuario_logado", "").lower()

    cid = usuario_logado in ["cid", "Cid"]
    admin = usuario_logado in ["cid", "Cid", "Cleo", "cleo"]
    familia = usuario_logado in ["cid", "cleo", "Cid", "Cleo","quiopa", "zanah"]


    if admin:
        opcoes_menu.append("Relatório de Vendas")

    if cid:
        opcoes_menu.extend(["AMV Tracker", "Protocolo Diário (POD)", "Painel de Cursos"])

    if familia:
        opcoes_menu.append("Estoque")

opcao = st.sidebar.radio("Escolha uma opção:", opcoes_menu)

if opcao == "Estoque":
    st.title("Controle de Estoque")
    # Agora a função ler_estoque_sheets() já retorna o DataFrame com os tipos corretos!
    df_estoque = ler_estoque_sheets()

    # Seção para administradores adicionarem itens
    if st.session_state.get("usuario_logado") in ["cid", "cleo"]:
        st.subheader("Adicionar/Incrementar Estoque")
        
        opcao_adicao = st.radio(
            "Escolha uma ação:",
            ["Adicionar Novo Item", "Incrementar Item Existente"],
            key="acao_estoque_radio",
            horizontal=True
        )
        
        # 1. Inicialize TODAS as variáveis que podem ser criadas condicionalmente.
        # Isso garante que elas sempre existam, evitando o NameError.
        novo_item_nome = None
        nova_variacao = None
        nova_quantidade = 1
        novo_preco = 0.0
        item_para_incrementar_str = None
        quantidade_incrementar = 1

        if opcao_adicao == "Adicionar Novo Item":
            # Formulário exclusivo para ADICIONAR um novo item
            with st.form("form_add_item", clear_on_submit=True):
                st.markdown("##### Preencha os dados do novo item:")
                novo_item_nome = st.text_input("Nome do Item", key="add_nome")
                nova_variacao = st.text_input("Variação (cor, tamanho, etc.)", key="add_variacao")
                nova_quantidade = st.number_input("Quantidade Inicial", min_value=1, step=1, key="add_qtd")
                novo_preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f", key="add_preco")
                
                submitted_add = st.form_submit_button("Adicionar Novo Item")

            if submitted_add:
                if novo_item_nome and nova_variacao:
                    adicionar_item_estoque(novo_item_nome, nova_variacao, nova_quantidade, novo_preco)
                    st.success(f'Item "{novo_item_nome} - {nova_variacao}" adicionado com sucesso!')
                    st.rerun()
                else:
                    st.error("Por favor, preencha o nome do item e a variação.")
        
        elif opcao_adicao == "Incrementar Item Existente":
            # Formulário exclusivo para INCREMENTAR um item existente
            with st.form("form_increment_item", clear_on_submit=True):
                st.markdown("##### Selecione o item e a quantidade a ser adicionada:")
                itens_existentes_com_variacao = [f"{row['Item']} - {row['Variação']}" for index, row in df_estoque.iterrows()]
                
                if not itens_existentes_com_variacao:
                    st.info("Não há itens no estoque para incrementar.")
                    submitted_increment = st.form_submit_button("Incrementar Estoque", disabled=True)
                else:
                    item_para_incrementar_str = st.selectbox("Selecione o item para incrementar", itens_existentes_com_variacao, key="inc_item")
                    quantidade_incrementar = st.number_input("Quantidade a Adicionar", min_value=1, step=1, key="inc_qtd")
                    submitted_increment = st.form_submit_button("Incrementar Estoque")

            if submitted_increment and itens_existentes_com_variacao:
                item_selecionado, variacao_selecionada = str(item_para_incrementar_str).split(" - ", 1)
                adicionar_item_estoque(item_selecionado, variacao_selecionada, quantidade_incrementar, preco=None)
                st.success(f'Estoque de "{item_para_incrementar_str}" incrementado com sucesso!')
                st.rerun()

    # Seção para registrar vendas
    st.subheader("Registrar Venda")
    if not df_estoque.empty:
        with st.form("form_venda"):
            itens_disponiveis = [f"{row['Item']} - {row['Variação']}" for index, row in df_estoque.iterrows()]
            item_vendido_str = st.selectbox("Selecione o item vendido", itens_disponiveis)
            quantidade_vendida = st.number_input("Quantidade Vendida", min_value=1, step=1)
            submitted_venda = st.form_submit_button("Registrar Venda")

            if submitted_venda:
                item_selecionado, variacao_selecionada = item_vendido_str.split(" - ")
                
                idx = df_estoque[(df_estoque['Item'] == item_selecionado) & (df_estoque['Variação'] == variacao_selecionada)].index[0] # type: ignore
                
                # A COMPARAÇÃO AGORA FUNCIONA PERFEITAMENTE!
                if df_estoque.loc[idx, 'Quantidade'] >= quantidade_vendida: # type: ignore
                    preco_unitario = df_estoque.loc[idx, 'Preço']
                    preco_total = quantidade_vendida * preco_unitario #  type: ignore
                    df_estoque.loc[idx, 'Quantidade'] -= quantidade_vendida # type: ignore
                    atualizar_estoque_sheets(df_estoque)
                    datahora = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y  %H:%M:%S")
                    registrar_venda_sheets(datahora, item_selecionado, variacao_selecionada, quantidade_vendida, preco_unitario, preco_total, st.session_state.nome_usuario)
                    st.success(f"Venda registrada! Total: R$ {preco_total:.2f}")
                    st.rerun()
                else:
                    st.error("Quantidade em estoque insuficiente para esta venda.")

    # Seção para mostrar o estoque atual
    st.subheader("Estoque Atual")
    if df_estoque.empty:
        st.info("Nenhum item em estoque.")
    else:
        df_estoque_display = df_estoque.copy()
        df_estoque_display['Quantidade'] = pd.to_numeric(df_estoque_display['Quantidade']).astype(int)
        df_estoque_display['Preço'] = pd.to_numeric(df_estoque_display['Preço']).map('R$ {:,.2f}'.format)
        height = (len(df_estoque_display) + 1) * 35
        st.dataframe(df_estoque_display, height=height, hide_index=True)

elif opcao == "Responder perguntas":
    st.subheader("Mapeamento e Desarmamento do 'Crítico Interno'")
    st.markdown("Use esta ferramenta para externalizar os pensamentos que te sabotam.")

    with st.form(key="formulario"):
        situacao = st.text_area("1. Situação (O que aconteceu?)"
        )
        pensamentos = st.text_area(
            "2. Pensamento Automático (O que o 'Crítico Interno' disse?)"
        )
        emocao = st.text_area(
            "3. Emoção / Sentimento (O que você sentiu? Nota 0-100.)"
        )
        conclusao = st.text_area(
            "4. Resposta Adaptativa (Como o 'Porto Seguro' analisaria isso?)"
        )
        resultado = ''
        
        submitted = st.form_submit_button("Enviar Respostas")

    if submitted:
        datahora = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y  %H:%M:%S")
        salvar_resposta_sheets(
            datahora, situacao, pensamentos, emocao, conclusao, 'Retirado', st.session_state.usuario_logado
        )
        st.success("Respostas salvas com sucesso no Excel!")
        st.subheader("Resumo das respostas:")
        st.write(f"**Data/Hora:** {datahora}")
        st.write(f"**Situação:** {situacao}")
        st.write(f"**Pensamentos automáticos:** {pensamentos}")
        st.write(f"**Emoção:** {emocao}")
        st.write(f"**Conclusão:** {conclusao}")
        st.write(f"**Resultado:** {'Retirado'}")

elif opcao == "Visualizar respostas":
    st.title("Respostas já registradas")
    if st.session_state.get("usuario_logado") in ["cid", "cleo"]:
        client = autenticar_gspread()
        sheet = client.open(SHEET_NAME)
        abas = [ws.title for ws in sheet.worksheets() if ws.title not in ["Usuarios", "Estoque", "Vendas"]]
        aba_escolhida = st.selectbox("Selecione o usuário/aba para visualizar:", abas)
        df_respostas = ler_respostas_sheets(aba_escolhida)
        st.write(f"Visualizando respostas da aba: **{aba_escolhida}**")
    else:
        df_respostas = ler_respostas_sheets(st.session_state.usuario_logado)

    if df_respostas.empty:
        st.info("Nenhuma resposta registrada ainda.")
    else:
        height = (len(df_respostas) + 1) * 35
        st.dataframe(df_respostas, height=height, hide_index=True)
        csv = df_respostas.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Baixar todas as respostas em CSV",
            data=csv,
            file_name="RPD.csv",
            mime="text/csv"
        )

elif opcao == "Relatório de Vendas":
    st.title("Relatório de Vendas")
    if st.session_state.get("usuario_logado") in ["cid", "cleo"]:
        client = autenticar_gspread()
        try:
            sheet = client.open(SHEET_NAME)
            worksheet = sheet.worksheet(WORKSHEET_VENDAS)
            df_vendas = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
            df_vendas = df_vendas.dropna(how="all")
            if df_vendas.empty:
                st.info("Nenhuma venda registrada ainda.")
            else:
                data_filtro = st.date_input("Filtrar vendas por dia")
                if data_filtro:
                    df_vendas['Data/Hora'] = pd.to_datetime(df_vendas['Data/Hora'], format='%d/%m/%Y  %H:%M:%S')
                    df_filtrado = df_vendas[df_vendas['Data/Hora'].dt.date == data_filtro]
                else:
                    df_filtrado = df_vendas

                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
                total_arrecadado = pd.to_numeric(df_filtrado['Preço Total']).sum()
                st.metric(label="Total Arrecadado (filtrado)", value=f"R$ {total_arrecadado:.2f}")

                st.subheader("Comissão do Dia")
                comissoes = {
                    "Cid": 0.30,
                    "Cleo": 0.20,
                    "Quiópa": 0.15,
                    "Zanah": 0.15,
                    "Caixa": 0.20
                }
                data_comissao = []
                for nome, percentual in comissoes.items():
                    valor_comissao = total_arrecadado * percentual
                    data_comissao.append({"Nome": nome, "Percentual": f"{percentual:.0%}", "Valor do Dia": f"R$ {valor_comissao:,.2f}"})
                
                df_comissao = pd.DataFrame(data_comissao)
                st.dataframe(df_comissao, hide_index=True)

                st.subheader("Itens em Falta ou com Baixo Estoque")
                df_estoque = ler_estoque_sheets()
                df_estoque['Quantidade'] = pd.to_numeric(df_estoque['Quantidade'])
                itens_em_falta = df_estoque[df_estoque['Quantidade'] <= 1]
                if itens_em_falta.empty:
                    st.info("Nenhum item com baixo estoque.")
                else:
                    height = (len(itens_em_falta) + 1) * 35
                    st.dataframe(itens_em_falta, height=height, hide_index=True)

        except gspread.exceptions.WorksheetNotFound:
            st.info("Nenhuma venda registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao ler o relatório de vendas: {e}")
    else:
        st.warning("Acesso restrito a administradores.")

elif opcao == "AMV Tracker":
    rebranding.exibir_painel_rebranding()

elif opcao == "Protocolo Diário (POD)":
    protocolo_diario.exibir_protocolo_diario()

elif opcao == "Painel de Cursos":
    cursos.exibir_painel_cursos()
