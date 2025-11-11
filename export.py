import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
from datetime import datetime

class ExportManager:
    def __init__(self):
        self.config_email = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'email_from': os.getenv('EMAIL_FROM', 'seuemail@gmail.com'),
            'email_password': os.getenv('EMAIL_PASSWORD', 'sua_senha'),
            'email_to': os.getenv('EMAIL_TO', 'destinatario@empresa.com')
        }
    
    def gerar_excel(self, dados, nome_loja):
        """Gera arquivo Excel com os dados da contagem"""
        
        # Criar DataFrame
        df = pd.DataFrame(dados)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contagem_chassi_{nome_loja}_{timestamp}.xlsx"
        
        # Criar Excel com formatação
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Contagem', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Contagem']
            
            # Formatar cabeçalho
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustar largura das colunas
            worksheet.set_column('A:A', 20)  # Chassi
            worksheet.set_column('B:B', 20)  # Timestamp
            worksheet.set_column('C:F', 15)  # Descrição, Modelo, Montador, Status
            worksheet.set_column('G:G', 15)  # EAN
        
        return filename
    
    def enviar_email(self, filename, nome_loja):
        """Envia o arquivo Excel por email"""
        
        try:
            # Configurar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.config_email['email_from']
            msg['To'] = self.config_email['email_to']
            msg['Subject'] = f"Relatório de Contagem - {nome_loja} - {datetime.now().strftime('%d/%m/%Y')}"
            
            # Corpo do email
            body = f"""
            Prezados,
            
            Segue em anexo o relatório de contagem de chassis da loja {nome_loja}.
            
            Data da contagem: {datetime.now().strftime('%d/%m/%Y %H:%M')}
            Total de chassis registrados: Consulte o arquivo em anexo.
            
            Att.,
            Sistema de Controle de Chassi
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Anexar arquivo
            with open(filename, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
            
            # Enviar email
            server = smtplib.SMTP(self.config_email['smtp_server'], self.config_email['smtp_port'])
            server.starttls()
            server.login(self.config_email['email_from'], self.config_email['email_password'])
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar email: {str(e)}")
            return False