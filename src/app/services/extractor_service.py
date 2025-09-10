import os
from typing import Optional, Tuple, List, Dict, Any
from app.extrator.extrator_extrato import ExtratorExtratoBancario
from app.core.config import settings

def extract_from_pdf_path(bank_code, pdf_path: str, make_xlsx: bool = True) -> Tuple[List[Dict[str, Any]], Optional[str], Dict[str, float]]:
    """
    Retorna: (lancamentos, xlsx_filename, totais)
    """
    extrator = ExtratorExtratoBancario()
    texto = extrator.extrair_texto_pdf(pdf_path)
    if not texto.strip():
        return [], None, dict(total_debitos=0.0, total_creditos=0.0, saldo_liquido=0.0)

    lancamentos = extrator.extrair_lancamentos(bank_code, texto)

    total_debitos = sum(l['Valor'] for l in lancamentos if l.get('Movimento') == 'DÉBITO')
    total_creditos = sum(l['Valor'] for l in lancamentos if l.get('Movimento') == 'CRÉDITO')
    saldo_liquido = (total_creditos - total_debitos)

    xlsx_filename = None
    if make_xlsx and lancamentos:
        xlsx_filename = os.path.basename(pdf_path).rsplit(".", 1)[0] + "_processado.xlsx"
        xlsx_fullpath = os.path.join(settings.STORAGE_EXPORTS, xlsx_filename)
        extrator.salvar_planilha(lancamentos, xlsx_fullpath)

    return lancamentos, xlsx_filename, dict(
        total_debitos=total_debitos,
        total_creditos=total_creditos,
        saldo_liquido=saldo_liquido
    )