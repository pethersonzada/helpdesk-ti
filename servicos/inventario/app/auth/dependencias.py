"""Autorização local com JWT assinado pelo serviço de Usuários."""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO

esquema = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Ator:
    id: int
    perfil: str
    token: str

def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> Ator:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Faça login para continuar.", headers={"WWW-Authenticate": "Bearer"})
    try:
        dados = jwt.decode(
            credenciais.credentials, JWT_SEGREDO,
            algorithms=[JWT_ALGORITMO], issuer=JWT_EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss", "perfil"]},
        )
        identificador = int(dados["sub"])
        perfil = dados["perfil"]
        if identificador < 1 or perfil not in ("admin", "tecnico", "solicitante"):
            raise ValueError("Identidade inválida")
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Faça login para continuar.", headers={"WWW-Authenticate": "Bearer"})
    return Ator(id=identificador, perfil=perfil, token=credenciais.credentials)

def exigir_perfil(*perfis: str):
    def verificar(usuario: Ator = Depends(usuario_atual)) -> Ator:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar
