"""Configurações do serviço de usuarios, carregadas do ambiente."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))
TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "1") == "1"

def carregar_segredo() -> str:
    segredo = os.getenv("JWT_SEGREDO", "")
    if not segredo and os.getenv("JWT_SEGREDO_ARQUIVO"):
        segredo = Path(os.environ["JWT_SEGREDO_ARQUIVO"]).read_text(encoding="utf-8").strip()
    if len(segredo) < 32:
        raise RuntimeError("Configure JWT_SEGREDO com pelo menos 32 caracteres ou JWT_SEGREDO_ARQUIVO.")
    return segredo

JWT_SEGREDO = carregar_segredo()
