import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timezone, timedelta

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

# Inicializar sessão
if 'scans' not in st.session_state:
    st.session_state.scans = []
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = ""
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0

def conectar_banco():
    """Conecta ao banco Neon"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["NEON_HOST"],
            database=st.secrets["NEON_DATABASE"],
            user=st.secrets["NEON_USER"],
            password=st.secrets["NEON_PASSWORD"],
            port=st.secrets["NEON_PORT"],
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def registrar_scan(ean_numero):
    """Registra um scan de EAN - ACEITA MÚLTIPLAS LEITURAS DO MESMO CÓDIGO"""
    if not ean_numero:
        return
        
    # Consultar banco
    conn = conectar_banco()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT sku, descricao FROM producao WHERE ean = %s", (ean_numero,))
            resultado = cur.fetchone()
            
            if resultado:
                sku, descricao = resultado
                registro = {
                    'ean': ean_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'sku': sku,
                    'descricao': descricao,
                    'status': 'Encontrado'
                }
                st.success(f"✅ {ean_numero} - {sku} - {descricao}")
            else:
                registro = {
                    'ean': ean_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'sku': 'N/A',
                    'descricao': 'Não encontrado',
                    'status': 'Não encontrado'
                }
                st.error(f"❌ {ean_numero} - Não encontrado")
            
            # SEMPRE adiciona o registro, mesmo que seja o mesmo EAN
            st.session_state.scans.append(registro)
            cur.close()
            conn.close()
            
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
    else:
        st.error("❌ Erro de conexão com o banco")

def finalizar_contagem(operador):
    """Finaliza a contagem - gera Excel simplificado"""
    try:
        # 1. Criar DataFrame de todos os scans
        df_scans = pd.DataFrame(st.session_state.scans)
        
        # 2. Filtrar apenas os encontrados e agrupar para o sumário final
        df_sumario = df_scans[df_scans['status'] == 'Encontrado'].groupby(['sku', 'descricao']).size().reset_index(name='Quantidade')
        df_sumario.columns = ['SKU', 'Descrição', 'Quantidade']
        df_sumario = df_sumario.sort_values('Quantidade', ascending=False)
        
        # 3. Gerar Excel FORMATADO (simplificado)
        filename = criar_excel_formatado(df_sumario, operador)
        
        # 4. Estatísticas para o email
        total_scans = len(st.session_state.scans)
        encontrados = len(df_scans[df_scans['status'] == 'Encontrado'])
        nao_encontrados = len(df_scans[df_scans['status'] == 'Não encontrado'])
        
        # 5. Enviar email automático
        enviou_email = enviar_email_automatico(filename, operador, df_sumario, total_scans, encontrados, nao_encontrados)
        
        # Mostrar sucesso
        st.balloons()
        st.success("🎉 CONTAGEM FINALIZADA COM SUCESSO!")
        
        # Estatísticas finais
        total_skus = len(df_sumario)
        total_unidades = df_sumario['Quantidade'].sum() if len(df_sumario) > 0 else 0
        
        st.info(f"""
        RELATORIO GERADO:
        - Loja/Operador: {operador}
        - Total de Scans: {total_scans}
        - Encontrados: {encontrados}
        - Não encontrados: {nao_encontrados}
        - SKUs diferentes: {total_skus}
        - Total de Unidades Contadas: {total_unidades}
        - Email enviado: {"Sim" if enviou_email else "Não"}
        """)
        
        # Botão para baixar Excel
        with open(filename, "rb") as f:
            st.download_button(
                "📥 BAIXAR PLANILHA EXCEL (SKU, Descrição, Quantidade)",
                f,
                filename,
                "application/vnd.ms-excel",
                use_container_width=True,
                type="primary"
            )
            
    except Exception as e:
        st.error(f"❌ Erro ao finalizar: {str(e)}")

def criar_excel_formatado(df_sumario, operador):
    """Cria um Excel formatado com apenas o Sumário por SKU (simplificado)"""
    
    # Criar workbook
    wb = Workbook()
    ws_sumario = wb.active
    ws_sumario.title = "Sumário por SKU"
    
    # Definir estilos
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="2E86AB", end_color="2E86AB", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                    top=Side(style='thin'), bottom=Side(style='thin'))
    center_align = Alignment(horizontal='center', vertical='center')
    
    # Título principal
    ws_sumario.merge_cells('A1:C1')
    ws_sumario['A1'] = f"RELATÓRIO DE CONTAGEM POR SKU - {operador}"
    ws_sumario['A1'].font = Font(bold=True, size=16, color="2E86AB")
    ws_sumario['A1'].alignment = center_align
    
    # Informações da loja e data
    ws_sumario.merge_cells('A2:C2')
    ws_sumario['A2'] = f"Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}"
    ws_sumario['A2'].font = Font(bold=True, size=12)
    ws_sumario['A2'].alignment = center_align
    
    # Cabeçalhos das colunas
    headers = ['SKU', 'Descrição', 'Quantidade']
    for col, header in enumerate(headers, 1):
        cell = ws_sumario.cell(row=4, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center_align
        ws_sumario.column_dimensions[chr(64 + col)].width = 25
    
    # Dados
    for row_idx, (index, row) in enumerate(df_sumario.iterrows(), 5):
        for col_idx, value in enumerate([row['SKU'], row['Descrição'], row['Quantidade']], 1):
            cell = ws_sumario.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.border = border
            cell.alignment = Alignment(horizontal='left', vertical='center')
    
    # Nome do arquivo
    filename = f"contagem_sku_{operador}_{datetime.now(fuso_brasilia).strftime('%Y%m%d_%H%M')}.xlsx"
    
    # Salvar arquivo
    wb.save(filename)
    return filename

def main():
    st.markdown("<h1 style='color: #FFD700; font-size: 3rem;'>Controle de Contagem por SKU</h1>", unsafe_allow_html=True)
    
    # Formulário de leitura
    scan_container = st.container()

    # Campo para nome da loja/operador
    operador = st.text_input("🏪 Loja/Operador:", placeholder="Digite o nome da loja/operador", key="operador_input")

    # Campo para leitura do código EAN
    with scan_container:
        scan_input = st.text_input(
            "Digite o código de barras (EAN) ou use leitor:",
            placeholder="⬅️ POSICIONE O LEITOR AQUI - O CAMPO ESTÁ PRONTO E COM FOCO AUTOMÁTICO",
            key=f"scan_input_{st.session_state.input_key}",
            label_visibility="visible"
        )

    # Verifica se há um novo scan para registrar
    if scan_input and len(scan_input.strip()) == 13:
        ean_numero = scan_input.strip()
        registrar_scan(ean_numero)
        
        # Incrementa a key para forçar novo campo limpo
        st.session_state.input_key += 1
        
        # Força o rerun para limpar o campo e refocar
        st.experimental_rerun()

    # Instruções para uso com leitor de código de barras
    st.info("""
    **INSTRUÇÕES:**
    - Posicione o leitor de código de barras no campo acima
    - **O CAMPO JÁ ESTÁ COM FOCO AUTOMÁTICO** - não precisa clicar
    - O sistema registra automaticamente códigos EAN de 13 dígitos
    - **MESMO CÓDIGO PODE SER LID VÁRIAS VEZES** - cada scan é contado individualmente
    - Após cada leitura, o campo é limpo automaticamente e pronto para a próxima
    - Use o botão 'Nova Contagem' para reiniciar
    - Use 'FINALIZAR CONTAGEM' para gerar relatório
    """)

    # Sidebar FIXA
    with st.sidebar:
        st.divider()
        
        # Contador
        st.metric("📋 Scans Registrados", len(st.session_state.scans))
        
        st.divider()
        
        # Botão de nova contagem
        if st.button("🔄 Nova Contagem", use_container_width=True, type="secondary"):
            st.session_state.scans = []
            st.session_state.last_scan = ""
            st.session_state.input_key += 1
            st.experimental_rerun()
        
        # Botão finalizar (só aparece se tiver scans)
        if st.session_state.scans:
            if st.button("✅ FINALIZAR CONTAGEM", use_container_width=True, type="primary"):
                if operador:
                    finalizar_contagem(operador)
                else:
                    st.warning("⚠️ Digite o nome da loja")

    # Lista de scans registrados
    if st.session_state.scans:
        st.header("📋 Scans Registrados (Resumo)")
        
        # Criar DataFrame para o sumário
        df_scans = pd.DataFrame(st.session_state.scans)
        
        # Agrupar e somar as quantidades
        df_sumario = df_scans.groupby(['sku', 'descricao']).size().reset_index(name='Quantidade')
        df_sumario.columns = ['SKU', 'Descrição', 'Quantidade']
        df_sumario = df_sumario.sort_values('Quantidade', ascending=False)
        
        st.dataframe(df_sumario, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
