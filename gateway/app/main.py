"""Gateway HTTP: mantém as rotas públicas e a tela na porta 8000."""
import asyncio
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse, Response

from app.seguranca_http import CabecalhosDeSeguranca

WEB = Path(__file__).resolve().parent.parent / "web"
DOCS_ATIVA = os.getenv("DOCS", "1") == "1"
SERVICOS = {
    "usuarios": os.getenv("URL_USUARIOS", "http://usuarios:8000").rstrip("/"),
    "inventario": os.getenv("URL_INVENTARIO", "http://inventario:8000").rstrip("/"),
    "chamados": os.getenv("URL_CHAMADOS", "http://chamados:8000").rstrip("/"),
}
ROTAS = {
    "auth": "usuarios",
    "usuarios": "usuarios",
    "ativos": "inventario",
    "chamados": "chamados",
    "notificacoes": "chamados",
}
app = FastAPI(title="HelpDesk TI | Gateway", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CabecalhosDeSeguranca)

@app.get("/", include_in_schema=False)
def tela():
    return FileResponse(WEB / "index.html")

@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(WEB / "app.js", media_type="text/javascript")

@app.get("/estilo.css", include_in_schema=False)
def estilo():
    return FileResponse(WEB / "estilo.css", media_type="text/css")

@app.get("/saude", include_in_schema=False)
async def saude():
    async def verificar(nome: str, endereco: str):
        try:
            async with httpx.AsyncClient(timeout=1.5) as cliente:
                resposta = await cliente.get(f"{endereco}/saude")
                return nome, "ok" if resposta.status_code == 200 else "indisponível"
        except httpx.RequestError:
            return nome, "indisponível"

    resultados = await asyncio.gather(*(verificar(nome, url) for nome, url in SERVICOS.items()))
    return {"status": "ok" if all(estado == "ok" for _, estado in resultados) else "parcial",
            "servicos": dict(resultados)}

@app.get("/docs", include_in_schema=False)
def documentacao():
    if not DOCS_ATIVA:
        raise HTTPException(status_code=404, detail="Documentação desabilitada.")
    return get_swagger_ui_html(openapi_url="/openapi.json", title="HelpDesk TI | APIs")

@app.get("/openapi.json", include_in_schema=False)
async def documentacao_integrada():
    """Reúne os esquemas OpenAPI dos serviços, conservando os caminhos públicos."""
    if not DOCS_ATIVA:
        raise HTTPException(status_code=404, detail="Documentação desabilitada.")
    resultado = {"openapi": "3.1.0", "info": {"title": "HelpDesk TI", "version": "3.0.0"},
                 "paths": {}, "components": {"schemas": {}, "securitySchemes": {}}}
    async with httpx.AsyncClient(timeout=3.0) as cliente:
        for nome, url in SERVICOS.items():
            try:
                resposta = await cliente.get(f"{url}/openapi.json")
                resposta.raise_for_status()
                esquema = resposta.json()
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
                continue
            resultado["paths"].update(esquema.get("paths", {}))
            for chave in ("schemas", "securitySchemes"):
                resultado["components"][chave].update(esquema.get("components", {}).get(chave, {}))
    return JSONResponse(resultado)

@app.api_route("/{caminho:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def encaminhar(caminho: str, request: Request):
    destino = ROTAS.get(caminho.split("/", 1)[0])
    if destino is None:
        raise HTTPException(status_code=404, detail="Rota não encontrada.")

    url = f"{SERVICOS[destino]}/{caminho}"
    cabecalhos = {chave: valor for chave, valor in request.headers.items()
                  if chave.lower() in ("authorization", "content-type", "accept", "accept-language")}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0), follow_redirects=False) as cliente:
            resposta = await cliente.request(
                request.method, url, params=request.query_params,
                content=await request.body(), headers=cabecalhos,
            )
    except httpx.RequestError as erro:
        raise HTTPException(status_code=503, detail=f"O serviço de {destino} está indisponível.") from erro

    cabecalhos_resposta = {chave: valor for chave, valor in resposta.headers.items()
                          if chave.lower() in ("content-type", "www-authenticate", "cache-control")}
    return Response(content=resposta.content, status_code=resposta.status_code, headers=cabecalhos_resposta)
