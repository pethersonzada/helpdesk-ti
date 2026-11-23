"""Serviço independente de Chamados, responsável também pelos avisos locais."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.chamados import modelos as modelos_chamados
from app.notificacoes import modelos as modelos_notificacoes
from app.chamados.rotas import router as chamados_router
from app.notificacoes.rotas import router as notificacoes_router
from app.config import DOCS_ATIVA
from app.database import Base, engine
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from app.seguranca_http import CabecalhosDeSeguranca

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(
    title="HelpDesk TI | Chamados", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(chamados_router)
app.include_router(notificacoes_router)

@app.exception_handler(NaoEncontrado)
def tratar_nao_encontrado(request: Request, erro: NaoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(erro)})

@app.exception_handler(RegraDeNegocio)
def tratar_regra(request: Request, erro: RegraDeNegocio):
    return JSONResponse(status_code=422, content={"detail": str(erro)})

@app.exception_handler(SemPermissao)
def tratar_permissao(request: Request, erro: SemPermissao):
    return JSONResponse(status_code=403, content={"detail": str(erro)})

@app.exception_handler(IntegrityError)
def tratar_conflito(request: Request, erro: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "O registro conflita com outro já existente."})

@app.get("/saude")
def saude():
    return {"status": "ok"}
