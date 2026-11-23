"""Valida o contrato público dos três serviços através do gateway."""
import os
import uuid
from datetime import datetime

import httpx
import pytest

BASE_URL = os.getenv("TEST_GATEWAY_URL", "http://127.0.0.1:8000")
SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")

@pytest.fixture(scope="module")
def cliente():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c

@pytest.fixture(scope="module")
def contas(cliente):
    resultado = {}
    for nome in ("admin", "ana", "bruno", "carla"):
        r = cliente.post("/auth/login", json={"email": f"{nome}@empresa.com", "senha": SENHA})
        assert r.status_code == 200, (nome, r.text)
        dados = r.json()
        resultado[nome] = {"headers": {"Authorization": f"Bearer {dados['access_token']}"},
                           "id": dados["usuario"]["id"]}
    return resultado

def abrir(cliente, contas, ativo_id=1, prioridade="alta"):
    return cliente.post("/chamados", headers=contas["ana"]["headers"],
                        json={"titulo": f"Teste {uuid.uuid4().hex[:12]}",
                              "descricao": "Chamado de integração via API Gateway",
                              "prioridade": prioridade, "ativo_id": ativo_id})

def test_saude_dos_servicos(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json()["servicos"] == {"usuarios": "ok", "inventario": "ok", "chamados": "ok"}

def test_autenticacao_obrigatoria(cliente):
    for caminho in ("/usuarios", "/ativos", "/chamados", "/notificacoes"):
        assert cliente.get(caminho).status_code == 401, caminho
        assert cliente.get(caminho, headers={"Authorization": "Bearer token-falso"}).status_code == 401, caminho

def test_usuarios_e_equipamentos(cliente, contas):
    assert cliente.get("/usuarios", headers=contas["ana"]["headers"]).status_code == 200
    ativos = cliente.get("/ativos", headers=contas["carla"]["headers"])
    assert ativos.status_code == 200 and any(ativo["id"] == 1 for ativo in ativos.json())

def test_permissoes(cliente, contas):
    assert cliente.post("/usuarios", headers=contas["ana"]["headers"],
                        json={"nome": "Outro", "email": "outro@empresa.com",
                              "perfil": "admin", "senha": "Senha1234"}).status_code == 403
    assert cliente.post("/ativos", headers=contas["ana"]["headers"],
                        json={"patrimonio": "PAT-123", "tipo": "rede",
                              "descricao": "Switch", "setor": "TI"}).status_code == 403
    chamado = abrir(cliente, contas)
    assert chamado.status_code == 201, chamado.text
    cid = chamado.json()["id"]
    assert cliente.get(f"/chamados/{cid}", headers=contas["bruno"]["headers"]).status_code == 404
    assert cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["ana"]["headers"],
                         json={"tecnico_id": contas["carla"]["id"]}).status_code == 403

def test_fluxo_completo_e_notificacoes(cliente, contas):
    r = abrir(cliente, contas, prioridade="critica")
    assert r.status_code == 201, r.text
    chamado = r.json()
    prazo = datetime.fromisoformat(chamado["prazo_sla"]) - datetime.fromisoformat(chamado["criado_em"])
    assert round(prazo.total_seconds() / 3600) == 4
    cid = chamado["id"]

    avisos = cliente.get("/notificacoes", headers=contas["ana"]["headers"])
    assert avisos.status_code == 200
    assert any(aviso["tipo"] == "ChamadoAberto" for aviso in avisos.json())

    tecnico = contas["carla"]["headers"]
    atribuir = cliente.patch(f"/chamados/{cid}/atribuir", headers=tecnico,
                            json={"tecnico_id": contas["carla"]["id"]})
    assert atribuir.status_code == 200, atribuir.text
    assert atribuir.json()["status"] == "em_atendimento"

    comentario = cliente.post(f"/chamados/{cid}/comentarios", headers=tecnico,
                             json={"texto": "Verificando o equipamento."})
    assert comentario.status_code == 201
    assert comentario.json()["autor_id"] == contas["carla"]["id"]

    resolver = cliente.patch(f"/chamados/{cid}/status", headers=tecnico,
                            json={"status": "resolvido"})
    assert resolver.status_code == 200 and resolver.json()["status"] == "resolvido"

    fechar = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"],
                          json={"status": "fechado"})
    assert fechar.status_code == 200 and fechar.json()["status"] == "fechado"
    assert len(fechar.json()["comentarios"]) == 1

    painel = cliente.get("/chamados/painel", headers=tecnico)
    assert painel.status_code == 200
    assert painel.json()["total"] >= 1

def test_validacao_de_dependencias(cliente, contas):
    assert abrir(cliente, contas, ativo_id=999999).status_code == 404
    r = abrir(cliente, contas, ativo_id=None)
    assert r.status_code == 201
    cid = r.json()["id"]
    rejeitado = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"],
                             json={"tecnico_id": contas["ana"]["id"]})
    assert rejeitado.status_code == 422, rejeitado.text

def test_documentacao_integrada(cliente):
    r = cliente.get("/openapi.json")
    assert r.status_code == 200
    caminhos = r.json()["paths"]
    assert "/auth/login" in caminhos
    assert "/ativos" in caminhos
    assert "/chamados" in caminhos
