import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timezone, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# Importar para formatação do Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

st.set_page_config(
    page_title="Salim Outlet - Controle de Contagem por SKU", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fuso horário de Brasília
fuso_brasilia = timezone(timedelta(hours=-3))

# Inicializar sessão - Mudando 'chassis' para 'scans' e 'last_chassi' para 'last_scan'
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

# A função criar_excel_formatado será drasticamente simplificada na próxima fase
# Por enquanto, vamos criar uma versão temporária para evitar erros
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

def enviar_email_automatico(arquivo, operador, df_sumario, total_scans, encontrados, nao_encontrados):
    """Envia email automaticamente com o sumário simplificado"""
    try:
        # Verificar se as configurações de email existem
        required_secrets = ["EMAIL_FROM", "EMAIL_PASSWORD", "SMTP_SERVER", "SMTP_PORT"]
        missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
        
        if missing_secrets:
            st.warning(f"⚠️ Email não configurado. Faltando: {', '.join(missing_secrets)}")
            return False
        
        # Lista de emails fixa
        emails_destino = st.secrets.get("EMAIL_TO", "contagem.salimoutlet@gmail.com").split(",")
        emails_destino = [email.strip() for email in emails_destino if email.strip()]
        
        # Preparar email - ASSUNTO DINÂMICO COM NOME DA LOJA
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = ", ".join(emails_destino)
        msg['Subject'] = f"Relatório de Contagem SKU - {operador} - {datetime.now(fuso_brasilia).strftime('%d/%m/%Y')}"
        
        # Estatísticas para o email
        total_skus = len(df_sumario)
        total_unidades = df_sumario['Quantidade'].sum() if len(df_sumario) > 0 else 0
        
        # Corpo do email
        body = f"""
        RELATÓRIO DE CONTAGEM POR SKU - SALIM OUTLET
        
        Data: {datetime.now(fuso_brasilia).strftime('%d/%m/%Y %H:%M')}
        Loja/Operador: {operador}
        
        RESUMO:
        • Total de Scans: {total_scans}
        • Encontrados: {encontrados}
        • Não encontrados: {nao_encontrados}
        • SKUs diferentes: {total_skus}
        • Total de Unidades Contadas: {total_unidades}
        
        O arquivo Excel em anexo contém o sumário final por SKU (SKU, Descrição, Quantidade).
        
        --
        Sistema de Controle de Contagem por SKU
        Salim Outlet
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Anexar arquivo
        with open(arquivo, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{arquivo}"')
        msg.attach(part)
        
        # Enviar email
        try:
            server = smtplib.SMTP_SSL(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
        except:
            server = smtplib.SMTP(st.secrets["SMTP_SERVER"], int(st.secrets["SMTP_PORT"]))
            server.starttls()
            server.login(st.secrets["EMAIL_FROM"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
            server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"❌ Erro no envio de email: {str(e)}")
        return False

def main():
    # Cabeçalho
    st.markdown(
        """
        <h1 style='
            color: #FFD700; 
            margin-bottom: 20px; 
            font-size: 5rem;
            text-shadow: 
                -2px -2px 0 #000,
                2px -2px 0 #000,
                -2px 2px 0 #000,
                2px 2px 0 #000,
                -3px 0px 0 #000,
                3px 0px 0 #000,
                0px -3px 0 #000,
                0px 3px 0 #000;
            font-weight: bold;
            text-align: center;
        '>Salim Outlet - Controle de Contagem por SKU</h1>
        """,
        unsafe_allow_html=True
    )
    
    st.divider()
    
    # Área principal - Formulário de leitura
    st.header("📝 Leitura de Código de Barras (EAN)")
    
    # Container para o campo de leitura
    scan_container = st.container()
    
    with scan_container:
        # Campo de leitura com key dinâmica
        # Adicionando um ID HTML previsível ao campo de entrada para o JS focar
        SCAN_INPUT_ID = "ean_scan_input"
        
        scan_input = st.text_input(
            "Digite o código de barras (EAN) ou use leitor:",
            placeholder="⬅️ POSICIONE O LEITOR AQUI - O CAMPO ESTÁ PRONTO",
            key=f"scan_input_{st.session_state.input_key}",
            label_visibility="visible"
        )
          # Injetando JavaScript para adicionar o ID ao elemento input real
        # O Streamlit não permite definir o ID diretamente, então usamos JS para encontrá-lo
        # e dar um ID fixo para o script de foco usar.
        st.markdown(f"""
            <script>
                const inputElement = document.querySelector('[data-testid="stTextInput"] input[type="text"]');
                if (inputElement) {{
                    inputElement.id = "{SCAN_INPUT_ID}";
                }}
            </script>
        """, unsafe_allow_html=True)

    # JavaScript para focar no campo (Versão mais robusta)
    # O ID "ean_scan_input" é injetado no elemento input real logo acima
    st.markdown("""
    <script>
        // Função para tentar focar o campo
        function focusScanInput() {
            const input = document.getElementById('ean_scan_input');
            if (input) {
                input.focus();
                input.select();
                console.log('Campo de leitura focado via ID fixo');
                return true;
            }
            return false;
        }

        // Tenta focar imediatamente e depois de um pequeno atraso para garantir
        // que o elemento foi renderizado após o st.re253	        if (!focusScanInput()) {
254	            setTimeout(focusScanInput, 100); // Tenta novamente após 100ms
255	        }
256	    </script>
257	    """, unsafe_allow_html=True)
258	    
259	    # Verifica se há um novo scan para registrar (modo automático)
260	    # AQUI ESTÁ A MUDANÇA PRINCIPAL: Verifica se o input tem 13 dígitos
261	    if (scan_input and 
262	        scan_input.strip() and 
263	        scan_input != st.session_state.last_scan and
264	        len(scan_input.strip()) == 13): # Condição de 13 dígitos
265	        
266	        st.session_state.last_scan = scan_input
267	        registrar_scan(scan_input.strip())
268	        # Incrementa a key para forçar novo campo limpo
269	        st.session_state.input_key += 1
270	        # Força o rerun para limpar o campo
271	        st.rerun()
272	
273	    # Instruções para uso com leitor de código de barras
274	    st.success(""" use o leitor.*
    """)

    # Sidebar FIXA
    with st.sidebar:
        # Logo na sidebar (MANTIDO)
        # Assumindo que o arquivo 'salimoutlet.jpg' existe
        # st.image("salimoutlet.jpg", width=100) 
        st.title("Contagem por SKU")
        
        st.divider()
        
        # Campo para nome da loja
        operador = st.text_input(
            "🏪 Loja/Operador:",
            placeholder="Digite o nome da loja/operador",
            key="operador_input"
        )
        
        # Contador
        st.metric("📋 Scans Registrados", len(st.session_state.scans))
        
        st.divider()
        
        # Informação do modo automático
        st.info("🟢 **Modo Leitor Ativo**")
        st.caption("Gravação automática ao ler EAN de 13 dígitos")
        
        # Botão de nova contagem
        if st.button("🔄 Nova Contagem", use_container_width=True, type="secondary"):
            st.session_state.scans = []
            st.session_state.last_scan = ""
            st.session_state.input_key += 1
            st.rerun()
        
        st.divider()
        
        # Botão finalizar (só aparece se tiver scans)
        if st.session_state.scans:
            if st.button("✅ FINALIZAR CONTAGEM", use_container_width=True, type="primary"):
                if operador:
                    finalizar_contagem(operador)
                else:
                    st.warning("⚠️ Digite o nome da loja/operador")

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
        
        # Estatísticas rápidas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Scans", len(st.session_state.scans))
        with col2:
            st.metric("SKUs Diferentes", len(df_sumario))
            
        # Aviso sobre finalização
        if not st.session_state.get('operador_input'):
            st.warning("👆 **Digite o nome da loja/operador na sidebar para finalizar**")

def registrar_scan(ean_numero):
    """Registra um scan de EAN"""
    if not ean_numero:
        return
        
    # Não precisamos mais verificar duplicidade de EAN, pois o objetivo é contar
    # Se o mesmo EAN for bipado 5 vezes, ele deve ser contado 5 vezes.
    
    # Consultar banco
    conn = conectar_banco()
    if conn:
        try:
            cur = conn.cursor()
            # ASSUMIMOS QUE O CAMPO NO BANCO É 'ean' E BUSCAMOS 'sku' E 'descricao'
            # O campo 'montador' foi removido da busca
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
                st.success(f"✅ **{ean_numero}** - {sku} - {descricao}")
            else:
                registro = {
                    'ean': ean_numero,
                    'data': datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M"),
                    'sku': 'N/A',
                    'descricao': 'Não encontrado',
                    'status': 'Não encontrado'
                }
                st.error(f"❌ **{ean_numero}** - Não encontrado")
            
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
        
        # 4. Enviar email automático
        enviar_email_automatico(filename, operador, df_sumario, total_scans, encontrados, nao_encontrados)
        
        # Mostrar sucesso
        st.balloons()
        st.success("🎉 **CONTAGEM FINALIZADA COM SUCESSO!**")
        
        # Estatísticas finais
        total_scans = len(st.session_state.scans)
        encontrados = len(df_scans[df_scans['status'] == 'Encontrado'])
        nao_encontrados = len(df_scans[df_scans['status'] == 'Não encontrado'])
        total_skus = len(df_sumario)
        total_unidades = df_sumario['Quantidade'].sum() if len(df_sumario) > 0 else 0
        
        st.info(f"""
        **📊 Relatório gerado:**
        - **🏪 Loja/Operador:** {operador}
        - **📦 Total de Scans:** {total_scans}
        - **✅ Encontrados:** {encontrados}
        - **❌ Não encontrados:** {nao_encontrados}
        - **📈 SKUs diferentes:** {total_skus}
        - **📄 Total de Unidades Contadas:** {total_unidades}
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

if __name__ == "__main__":
    main()
