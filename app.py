import streamlit as st
import pandas as pd
import time
from datetime import datetime
import json
import qrcode
from io import BytesIO
import base64

# Importar módulos personalizados
from database import Database
from export import ExportManager

# Configurar página
st.set_page_config(
    page_title="Controle de Chassi de Motos",
    page_icon="🏍️",
    layout="wide"
)

class ChassiApp:
    def __init__(self):
        self.db = Database()
        self.export_manager = ExportManager()
        self.initialize_session_state()
        
    def initialize_session_state(self):
        if 'loja_nome' not in st.session_state:
            st.session_state.loja_nome = ""
        if 'chassis_registrados' not in st.session_state:
            st.session_state.chassis_registrados = []
        if 'contagem_iniciada' not in st.session_state:
            st.session_state.contagem_iniciada = False
        if 'ultimo_chassi' not in st.session_state:
            st.session_state.ultimo_chassi = ""
    
    def mostrar_sidebar(self):
        with st.sidebar:
            st.title("🏍️ Configurações")
            
            # Input do nome da loja
            loja_nome = st.text_input(
                "Nome da Loja",
                value=st.session_state.loja_nome,
                placeholder="Digite o nome da sua loja"
            )
            
            if loja_nome != st.session_state.loja_nome:
                st.session_state.loja_nome = loja_nome
                st.rerun()
            
            st.divider()
            
            # Status da contagem
            st.subheader("Status da Contagem")
            st.write(f"Loja: **{st.session_state.loja_nome if st.session_state.loja_nome else 'Não definida'}**")
            st.write(f"Chassis registrados: **{len(st.session_state.chassis_registrados)}**")
            
            # Botões de controle
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Nova Contagem", use_container_width=True):
                    st.session_state.chassis_registrados = []
                    st.session_state.contagem_iniciada = True
                    st.session_state.ultimo_chassi = ""
                    st.rerun()
            
            with col2:
                if st.session_state.contagem_iniciada and st.session_state.chassis_registrados:
                    if st.button("✅ Finalizar", use_container_width=True, type="primary"):
                        self.finalizar_contagem()
    
    def mostrar_formulario_chassi(self):
        st.header("📝 Registrar Chassi")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Input manual do chassi
            chassi = st.text_input(
                "Número do Chassi",
                placeholder="Digite ou escaneie o código do chassi",
                key="chassi_input"
            )
            
            # Botão para adicionar chassi
            if st.button("➕ Adicionar Chassi", type="primary", use_container_width=True):
                if chassi:
                    self.processar_chassi(chassi)
                else:
                    st.warning("Por favor, digite um número de chassi")
        
        with col2:
            # Gerador de QR Code para teste
            st.subheader("Gerar QR Code (Teste)")
            teste_chassi = st.text_input("Chassi para teste", placeholder="Chassi exemplo", key="teste_chassi")
            if teste_chassi:
                self.gerar_qrcode(teste_chassi)
    
    def processar_chassi(self, chassi):
        """Processa um chassi, consulta informações e adiciona à lista"""
        if chassi in [c['chassi'] for c in st.session_state.chassis_registrados]:
            st.warning(f"⚠️ Chassi {chassi} já foi registrado!")
            return
        
        # Consultar informações no banco de dados
        info_moto = self.db.consultar_chassi(chassi)
        
        if info_moto:
            registro = {
                'chassi': chassi,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'descricao': info_moto.get('descricao', 'N/A'),
                'modelo': info_moto.get('modelo', 'N/A'),
                'montador': info_moto.get('montador', 'N/A'),
                'status': info_moto.get('status', 'N/A'),
                'ean': info_moto.get('ean', 'N/A')
            }
            st.success(f"✅ Chassi {chassi} encontrado e registrado!")
            
            # Mostrar detalhes do produto
            with st.expander("📋 Detalhes do Produto", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Descrição:** {info_moto.get('descricao', 'N/A')}")
                    st.write(f"**Modelo/SKU:** {info_moto.get('modelo', 'N/A')}")
                with col2:
                    st.write(f"**Montador:** {info_moto.get('montador', 'N/A')}")
                    st.write(f"**Status:** {info_moto.get('status', 'N/A')}")
                    st.write(f"**EAN:** {info_moto.get('ean', 'N/A')}")
                    
        else:
            registro = {
                'chassi': chassi,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'descricao': 'Não encontrado',
                'modelo': 'N/A',
                'montador': 'N/A',
                'status': 'Não encontrado',
                'ean': 'N/A'
            }
            st.error(f"❌ Chassi {chassi} não encontrado na base de dados!")
        
        st.session_state.chassis_registrados.append(registro)
        st.session_state.ultimo_chassi = chassi
        st.rerun()
    
    def gerar_qrcode(self, chassi):
        """Gera um QR Code para teste"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(chassi)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64 para exibir no Streamlit
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        st.image(f"data:image/png;base64,{img_str}", width=200)
        st.caption(f"QR Code para: {chassi}")
    
    def mostrar_lista_chassis(self):
        if st.session_state.chassis_registrados:
            st.header("📋 Chassis Registrados")
            
            # Converter para DataFrame para exibição
            df = pd.DataFrame(st.session_state.chassis_registrados)
            st.dataframe(df, use_container_width=True)
            
            # Estatísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Registrado", len(st.session_state.chassis_registrados))
            with col2:
                encontrados = len([c for c in st.session_state.chassis_registrados if c['status'] != 'Não encontrado'])
                st.metric("Encontrados na Base", encontrados)
            with col3:
                nao_encontrados = len([c for c in st.session_state.chassis_registrados if c['status'] == 'Não encontrado'])
                st.metric("Não Encontrados", nao_encontrados)
        else:
            st.info("ℹ️ Nenhum chassi registrado ainda. Use o formulário acima para adicionar chassis.")
    
    def finalizar_contagem(self):
        """Finaliza a contagem e exporta os dados"""
        if not st.session_state.loja_nome:
            st.error("Por favor, defina o nome da loja antes de finalizar!")
            return
            
        try:
            # Gerar arquivo Excel
            filename = self.export_manager.gerar_excel(
                st.session_state.chassis_registrados, 
                st.session_state.loja_nome
            )
            
            # Enviar por email (configurar no export.py)
            self.export_manager.enviar_email(filename, st.session_state.loja_nome)
            
            st.success("✅ Contagem finalizada com sucesso! Relatório enviado por email.")
            
            # Opção para download imediato
            with open(filename, "rb") as file:
                btn = st.download_button(
                    label="📥 Baixar Relatório Excel",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.ms-excel"
                )
            
        except Exception as e:
            st.error(f"Erro ao finalizar contagem: {str(e)}")
    
    def run(self):
        # Verificar se o nome da loja foi definido
        if not st.session_state.loja_nome:
            st.title("🏍️ Controle de Chassi de Motos")
            st.warning("⚠️ Por favor, defina o nome da sua loja na barra lateral para começar.")
            self.mostrar_sidebar()
            return
        
        # Interface principal
        st.title(f"🏍️ Controle de Chassi - {st.session_state.loja_nome}")
        
        # Layout principal
        self.mostrar_sidebar()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.mostrar_formulario_chassi()
            self.mostrar_lista_chassis()
        
        with col2:
            # Scanner de QR Code (simulado)
            st.header("📷 Scanner QR Code")
            st.info("""
            **Instruções:**
            1. Posicione a câmera sobre o QR Code
            2. O chassi será lido automaticamente
            3. As informações serão consultadas na base
            """)
            
            # Simulação de leitura de QR Code
            chassi_scanner = st.text_input(
                "Chassi do Scanner (Simulação)",
                placeholder="Resultado do scanner aparecerá aqui",
                key="scanner_input"
            )
            
            if chassi_scanner and chassi_scanner != st.session_state.ultimo_chassi:
                self.processar_chassi(chassi_scanner)

# Executar aplicação
if __name__ == "__main__":
    app = ChassiApp()
    app.run()