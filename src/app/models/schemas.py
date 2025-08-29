from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field

MovType = Literal["DÉBITO", "CRÉDITO", "INDEFINIDO"]

class Lancamento(BaseModel):
    Data: str
    Movimento: MovType
    Historico: str
    Valor: float
    Debito: Union[int, str, None] = None
    Credito: Union[int, str, None] = None

class ExtractResponse(BaseModel):
    total_lancamentos: int
    total_debitos: float
    total_creditos: float
    saldo_liquido: float
    xlsx_filename: Optional[str] = None
