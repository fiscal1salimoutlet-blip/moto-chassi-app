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

# Inicializar sessão
if 'scans' not in st.session_state:
    st.session_state.scans = []
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = ""
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0
if 'auto_focus' not in st.session_state:
    st.session_state.auto_focus = True

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
            st.warning(f"Email não configurado. Faltando: {', '.join(missing_secrets)}")
            return False
        
        # Lista de emails fixa
        emails_destino = st.secrets.get("EMAIL_TO", "contagem.salimoutlet@gmail.com").split(",")
        emails_destino = [email.strip() for email in emails_destino if email.strip()]
        
        # Preparar email - ASSUNTO DINÂMICO COM NOME DA LOJA
        msg = MIMEMultipart()
        msg['From'] = st.secrets["EMAIL_FROM"]
        msg['To'] = ", ".join(emails_destino)
        msg['Subject'] = f"Relatorio de Contagem SKU - {operador} - {datetime.now(fuso_brasilia).strftime('%d/%m/%Y')}"
        
        # Estatísticas para o email
        total_skus = len(df_sumario)
        total_unidades = df_sumario['Quantidade'].sum() if len(df_sumario) > 0 else 0
        
        # Corpo do email
        body = f"""
        RELATORIO DE CONTAGEM POR SKU - SALIM OUTLET
        
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
        st.error(f"Erro no envio de email: {str(e)}")
        return False

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

def main():
    # Cabeçalho
    st.markdown(
        """
        <h1 style='
            color: #FFD700; 
            margin-bottom: 20px; 
            font-size: 3rem;
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
    
    # JavaScript para auto foco - Versão melhorada
    st.markdown("""
    <script>
        function focusScanInput() {
            const inputs = parent.document.querySelectorAll('input[type=text]');
            for (let input of inputs) {
                if (input.value === "" || input.placeholder.includes("POSICIONE O LEITOR")) {
                    input.focus();
                    input.select();
                    break;
                }
            }
        }
        
        // Tenta focar imediatamente e depois de um delay
        setTimeout(focusScanInput, 100);
        setTimeout(focusScanInput, 500);
        setTimeout(focusScanInput, 1000);
        
        // Também foca quando o mouse passa sobre a área
        document.addEventListener('mousemove', focusScanInput);
    </script>
    """, unsafe_allow_html=True)
    
    # Container para o campo de leitura
    scan_container = st.container()
    
    with scan_container:
        # Campo de leitura com key dinâmica
        scan_input = st.text_input(
            "Digite o código de barras (EAN) ou use leitor:",
            placeholder="⬅️ POSICIONE O LEITOR AQUI - O CAMPO ESTÁ PRONTO E COM FOCO AUTOMÁTICO",
            key=f"scan_input_{st.session_state.input_key}",
            label_visibility="visible"
        )

    # Verifica se há um novo scan para registrar (modo automático)
    # REMOVIDA A VERIFICAÇÃO DE "scan_input != st.session_state.last_scan" 
    # para permitir múltiplas leituras do mesmo código
    scan_valido = (
        scan_input and 
        scan_input.strip() and 
        len(scan_input.strip()) == 13
    )
    
    if scan_valido:
        st.session_state.last_scan = scan_input
        registrar_scan(scan_input.strip())
        # Incrementa a key para forçar novo campo limpo
        st.session_state.input_key += 1
        # Força o rerun para limpar o campo
        st.rerun()

    # Instruções para uso com leitor de código de barras
    st.info("""
    **INSTRUÇÕES:**
    - Posicione o leitor de código de barras no campo acima
    - O sistema registra automaticamente códigos EAN de 13 dígitos
    - **MESMO CÓDIGO PODE SER LID VÁRIAS VEZES** - cada scan é contado individualmente
    - Cada scan válido será adicionado à lista abaixo
    - Use o botão 'Nova Contagem' para reiniciar
    - Use 'FINALIZAR CONTAGEM' para gerar relatório
    """)

    # Sidebar FIXA
    with st.sidebar:
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
        st.caption("✅ **Aceita múltiplas leituras do mesmo código**")
        
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Scans", len(st.session_state.scans))
        with col2:
            st.metric("SKUs Diferentes", len(df_sumario))
        with col3:
            total_unidades = df_sumario['Quantidade'].sum() if len(df_sumario) > 0 else 0
            st.metric("Total de Unidades", total_unidades)
            
        # Aviso sobre finalização
        if not operador:
            st.warning("👆 **Digite o nome da loja/operador na sidebar para finalizar**")

if __name__ == "__main__":
    main()