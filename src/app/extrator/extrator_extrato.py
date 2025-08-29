import PyPDF2
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import logging

class ExtratorExtratoBancario:
    def __init__(self):
        self.configurar_logs()
        self.configurar_padroes()
        
    def configurar_logs(self):
        """Configura o sistema de logs."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def configurar_padroes(self):
        """Configura os padrões regex para diferentes formatos de bancos."""
        # Padrões para diferentes formatos de data
        self.padroes_data = [
            re.compile(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b'),  # DD/MM/YYYY ou DD-MM-YYYY
            re.compile(r'\b(\d{1,2}[\/\-]\d{1,2})\b'),                # DD/MM (sem ano)
            re.compile(r'\b(\d{1,2}[\/\-](jan|fev|mar|abr|jun|jul|ago|set|out|nov|dez))\b', re.IGNORECASE), #DD/XXX (traduzir mês)
            re.compile(r'\b(\d{1,2}\s*[\/\-]\s*(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez))\b', re.IGNORECASE)
        ]

        self.meses_abrev = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        
        # Padrões para valores monetários com indicadores
        self.padroes_valor = [
            # Aceita: -1.234,56  |  1.234,56  |  1.234,56 D
        re.compile(r'(?P<valor>[+-]?\d{1,3}(?:\.\d{3})*,\d{2})(?:\s*(?P<ind>[DC]|\(\+\)|\(\-\)))?')
]
        
        # Palavras-chave para identificar linhas de transação
        self.palavras_transacao = [
            'pix', 'ted', 'doc', 'pagamento', 'saque', 'deposito', 'transferencia', 'dep', 'depósito',
            'boleto', 'tarifa', 'cheque', 'debito', 'credito', 'cobranca',
            'impostos', 'agua', 'água', 'luz', 'telefone', 'rende facil', 'rendimento', 'seguros',
            'seguro', 'pagto', 'consorcio', 'consórcio', 'rende', 'deb', 'cred','déb', 'créd', 'juros', 'iof', 'transf',
            'sispag', 'rend', 'rede', 'cob', 'tev', 'envio', 'dp', 'db', 'pg', 'fornecedor', 'recebimento'
        ]
    
    def extrair_texto_pdf(self, caminho_pdf: str) -> str:
        """
        Extrai texto de um arquivo PDF, tratando múltiplas páginas.
        
        Args:
            caminho_pdf (str): Caminho para o arquivo PDF
            
        Returns:
            str: Texto extraído do PDF
        """
        try:
            with open(caminho_pdf, 'rb') as arquivo:
                leitor = PyPDF2.PdfReader(arquivo)
                texto_completo = ""
                
                for i, pagina in enumerate(leitor.pages):
                    texto_pagina = pagina.extract_text()
                    if texto_pagina.strip():
                        texto_completo += f"\n--- PÁGINA {i+1} ---\n"
                        texto_completo += texto_pagina + "\n"
                
                self.logger.info(f"Texto extraído de {len(leitor.pages)} páginas")
                return texto_completo
                
        except Exception as e:
            self.logger.error(f"Erro ao extrair texto do PDF: {str(e)}")
            raise

    
    def detectar_data(self, linha: str) -> Optional[str]:
        for padrao in self.padroes_data:
            matches = list(padrao.finditer(linha))
            if matches:
                return self.normalizar_data(matches[-1].group(1))  # pega a última
        return None

    
    
    def detectar_valor_e_tipo(self, linha: str) -> Tuple[Optional[float], Optional[str]]:
        for padrao in self.padroes_valor:
            m = padrao.search(linha)
            if m:
                valor_str = m.group('valor')
                indicador = m.group('ind')
                valor = self.normalizar_valor(valor_str)
                if indicador:
                    tipo = self.identificar_tipo_movimento(indicador)
                else:
                    tipo = 'DÉBITO' if valor_str.strip().startswith('-') else 'CRÉDITO'
                return valor, tipo
        return None, None

    
    def converter_data_com_mes_abrev(self, data_str: str) -> str:
        """Converte data com mês abreviado (maiúsculas ou minúsculas)."""
        try:
            data_limpa = re.sub(r'\s+', '', data_str)
            data_limpa = data_limpa.replace('-', '/')
                                
            partes = data_limpa.split('/')
            if len(partes) != 2:
                return data_str
            
            dia, mes_abrev = partes
            dia = dia.zfill(2)
            mes_abrev = mes_abrev.strip()
            
            mes_num = None
            mes = mes_abrev.lower()
            
            if mes in self.meses_abrev:
                mes_num = self.meses_abrev[mes]
            elif mes_abrev in self.meses_abrev:  # Fallback
                mes_num = self.meses_abrev[mes_abrev]
            
            if mes_num:
                ano_atual = datetime.now().year
                return f"{dia}/{mes_num}/{ano_atual}"
            
            return data_str
            
        except Exception:
            return data_str
    
    def normalizar_data(self, data_str: str) -> str:
        """
        Normaliza diferentes formatos de data.
        
        Args:
            data_str (str): String da data
            
        Returns:
            str: Data normalizada no formato DD/MM/AAAA
        """
        try:
            data_limpa = data_str.strip()

            if any(mes.lower() in data_limpa.lower() for mes in ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']):
                return self.converter_data_com_mes_abrev(data_limpa)
            
            data_limpa = re.sub(r'[^\d\/\-]', '', data_str)
            
            # Se tem apenas DD/MM, adiciona o ano atual
            if len(data_limpa.split('/')) == 2 or len(data_limpa.split('-')) == 2:
                ano_atual = datetime.now().year
                data_limpa += f"/{ano_atual}"
            
            # Tenta diferentes formatos
            formatos = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y']
            
            for formato in formatos:
                try:
                    data_obj = datetime.strptime(data_limpa, formato)
                    return data_obj.strftime('%d/%m/%Y')
                except ValueError:
                    continue
                    
            return data_str
            
        except Exception:
            return data_str
    
    def normalizar_valor(self, valor_str: str) -> float:
        """
        Converte string de valor monetário brasileiro para float.
        
        Args:
            valor_str (str): String do valor (ex: "1.234,56")
            
        Returns:
            float: Valor convertido
        """
        try:
            # Remove espaços e caracteres especiais
            valor_limpo = valor_str.replace(' ', '').replace('(+)', '').replace('(-)', '')
            
            # Se tem pontos como separadores de milhares e vírgula como decimal
            if '.' in valor_limpo and ',' in valor_limpo:
                # Remove os pontos (milhares) e troca vírgula por ponto (decimal)
                valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            elif ',' in valor_limpo and '.' not in valor_limpo:
                # Apenas vírgula decimal
                valor_limpo = valor_limpo.replace(',', '.')
            
            # Remove caracteres não numéricos exceto ponto decimal
            valor_limpo = re.sub(r'[^\d\.\-\+]', '', valor_limpo)
            
            return abs(float(valor_limpo)) if valor_limpo else 0.0
            
        except Exception:
            return 0.0
    
    def identificar_tipo_movimento(self, indicador: str) -> str:
        """
        Identifica o tipo de movimento baseado no indicador.
        
        Args:
            indicador (str): Indicador D/C, +/-, (+)/(-)
            
        Returns:
            str: 'DÉBITO', 'CRÉDITO' ou 'INDEFINIDO'
        """
        indicador = indicador.upper().strip()
        
        if indicador in ['D', '-', '(-)']:
            return 'DÉBITO'
        elif indicador in ['C', '+', '(+)']:
            return 'CRÉDITO'
        else:
            return 'INDEFINIDO'
    
    def eh_linha_transacao(self, linha: str) -> bool:
        """
        Verifica se uma linha contém uma transação bancária.
        
        Args:
            linha (str): Linha do texto
            
        Returns:
            bool: True se é uma linha de transação
        """
        linha_lower = linha.lower()
        
        # Verifica se tem data E valor
        tem_data = any(padrao.search(linha) for padrao in self.padroes_data)
        tem_valor = any(padrao.search(linha) for padrao in self.padroes_valor)
        
        # Verifica se tem palavras-chave de transação
        tem_palavra_chave = any(palavra in linha_lower for palavra in self.palavras_transacao)
        
        # Ignora linhas de cabeçalho ou totais
        ignorar = any(termo in linha_lower for termo in [
            'agencia', 'conta corrente', 'cliente', 'periodo', 'saldo anterior',
            'total', 'pagina', '---', 'informacoes adicionais'
        ])
        
        return tem_data and tem_valor and tem_palavra_chave and not ignorar
    
    def extrair_historico(self, linha: str, data: str, valor_info: str) -> str:
        """
        Extrai o histórico/descrição removendo data e valor da linha.
        
        Args:
            linha (str): Linha completa
            data (str): Data encontrada
            valor_info (str): Informação do valor encontrada
            
        Returns:
            str: Histórico limpo
        """
        historico = linha
        
        # Remove a data
        for padrao in self.padroes_data:
            historico = padrao.sub('', historico)
        
        # Remove informações de valor
        for padrao in self.padroes_valor:
            historico = padrao.sub('', historico)
        
        # Limpa espaços extras e caracteres especiais
        historico = re.sub(r'\s+', ' ', historico).strip()
        historico = re.sub(r'^[-\s]+|[-\s]+$', '', historico)
        
        return historico[:100]  # Limita tamanho
    
    def processar_linha_extrato(self, bank_code, linha: str) -> Optional[Dict[str, any]]:
        """
        Processa uma linha do extrato e extrai as informações.
        
        Args:
            linha (str): Linha do extrato
            
        Returns:
            Optional[Dict[str, any]]: Dados extraídos ou None se inválida
        """
        if not self.eh_linha_transacao(linha):
            return None
        
        # Extrai data
        data = self.detectar_data(linha)
        if not data:
            return None
        
        # Extrai valor e tipo
        valor, tipo_movimento = self.detectar_valor_e_tipo(linha)
        if valor is None or valor == 0:
            return None
        
        # Extrai histórico
        historico = self.extrair_historico(linha, data, str(valor))
        
        # Monta o registro
        dados = {
            'Data': data,
            'Movimento': tipo_movimento,
            'Historico': historico,
            'Valor': valor,
            'Debito': bank_code if tipo_movimento == 'CRÉDITO' else '',
            'Credito': bank_code if tipo_movimento == 'DÉBITO' else ''
        }
        
        return dados
    
    def extrair_lancamentos(self, bank_code, texto_pdf: str) -> List[Dict[str, any]]:
        """
        Extrai todos os lançamentos do texto do PDF.
        
        Args:
            texto_pdf (str): Texto extraído do PDF
            
        Returns:
            List[Dict[str, any]]: Lista de lançamentos
        """
        linhas = texto_pdf.split('\n')
        lancamentos = []
        
        # Processa linha por linha
        for i, linha in enumerate(linhas):
            linha = linha.strip()
            
            if len(linha) < 5:  # Ignora linhas muito curtas
                continue
            
            # Tenta processar como transação
            dados = self.processar_linha_extrato(bank_code, linha)
            
            if dados:
                lancamentos.append(dados)
                self.logger.debug(f"Linha {i+1}: {dados['Data']} - {dados['Historico'][:30]}...")
            
            # Verifica se a próxima linha é continuação (para históricos quebrados)
            if i + 1 < len(linhas) and dados:
                proxima_linha = linhas[i + 1].strip()
                if (proxima_linha and 
                    not self.eh_linha_transacao(proxima_linha) and 
                    not any(padrao.search(proxima_linha) for padrao in self.padroes_data)):
                    # Adiciona à descrição do último lançamento
                    lancamentos[-1]['Historico'] += f" {proxima_linha[:50]}"
        
        # Remove duplicatas baseado em data, valor e primeiras palavras do histórico
        lancamentos_unicos = []
        chaves_vistas = set()
        
        for lancamento in lancamentos:
            chave = (
                lancamento['Data'],
                lancamento['Valor'],
                lancamento['Historico'][:20]
            )
            
            if chave not in chaves_vistas:
                chaves_vistas.add(chave)
                lancamentos_unicos.append(lancamento)
        
        self.logger.info(f"Extraídos {len(lancamentos_unicos)} lançamentos únicos de {len(lancamentos)} totais")
        return lancamentos_unicos
    
    def salvar_planilha(self, lancamentos: List[Dict[str, any]], arquivo_saida: str):
        """
        Salva os lançamentos em uma planilha Excel com formatação.
        
        Args:
            lancamentos (List[Dict[str, any]]): Lista de lançamentos
            arquivo_saida (str): Nome do arquivo de saída
        """
        try:
            if not lancamentos:
                self.logger.warning("Nenhum lançamento para salvar")
                return
            
            df = pd.DataFrame(lancamentos)
            
            # Reorganiza as colunas na ordem desejada
            colunas = ['Data', 'Movimento', 'Historico', 'Valor', 'Debito', 'Credito']
            df = df[colunas]
            
            # Ordena por data
            df['Data_Sort'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values('Data_Sort').drop('Data_Sort', axis=1)
            
            # Salva em Excel
            with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Extrato', index=False)
                
                # Ajusta larguras das colunas
                worksheet = writer.sheets['Extrato']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self.logger.info(f"Planilha salva em {arquivo_saida}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar planilha: {str(e)}")
            raise
    
            
            
                



