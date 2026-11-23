"""Integrações HTTP síncronas entre serviços, com token e tempo limite."""
import os
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from app.erros import NaoEncontrado, RegraDeNegocio

URL_USUARIOS = os.getenv("URL_USUARIOS", "http://usuarios:8000").rstrip("/")
URL_INVENTARIO = os.getenv("URL_INVENTARIO", "http://inventario:8000").rstrip("/")

@dataclass(frozen=True)
class UsuarioExterno:
    id: int
    perfil: str

def consultar(base: str, caminho: str, token: str, nome: str) -> dict:
    try:
        resposta = httpx.get(
            f"{base}{caminho}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(2.0, connect=1.0),
            follow_redirects=False,
        )
    except httpx.RequestError as erro:
        raise HTTPException(status_code=503, detail=f"O serviço de {nome} está indisponível.") from erro

    if resposta.status_code == 404:
        raise NaoEncontrado(f"Recurso não encontrado no serviço de {nome}.")
    if resposta.status_code == 422:
        raise RegraDeNegocio(f"Dados rejeitados pelo serviço de {nome}.")
    if resposta.status_code in (401, 403):
        raise HTTPException(status_code=resposta.status_code, detail=f"Acesso negado pelo serviço de {nome}.")
    if resposta.status_code >= 500:
        raise HTTPException(status_code=503, detail=f"O serviço de {nome} está indisponível.")
    if resposta.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Resposta inesperada do serviço de {nome}.")
    try:
        dados = resposta.json()
        if not isinstance(dados, dict):
            raise ValueError("Resposta não é um objeto JSON.")
        return dados
    except ValueError as erro:
        raise HTTPException(status_code=502, detail=f"Resposta inválida do serviço de {nome}.") from erro

def conferir_ativo(ativo_id: int, token: str) -> None:
    consultar(URL_INVENTARIO, f"/ativos/{ativo_id}", token, "Inventário")

def conferir_tecnico(usuario_id: int, token: str) -> UsuarioExterno:
    dados = consultar(URL_USUARIOS, f"/usuarios/{usuario_id}", token, "Usuários")
    if dados.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
    try:
        identificador = int(dados["id"])
        if identificador < 1:
            raise ValueError("Identificador inválido.")
    except (KeyError, ValueError, TypeError) as erro:
        raise HTTPException(status_code=502, detail="Resposta inválida do serviço de Usuários.") from erro
    return UsuarioExterno(id=identificador, perfil=dados["perfil"])
