"""Testes de segurança dos microsserviços através do API Gateway."""
import os
import uuid

import httpx
import jwt
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
    for apelido in ("admin", "ana", "bruno", "carla"):
        resposta = cliente.post("/auth/login", json={"email": f"{apelido}@empresa.com", "senha": SENHA})
        assert resposta.status_code == 200, resposta.text
        dados = resposta.json()
        resultado[apelido] = {"id": dados["usuario"]["id"],
                             "headers": {"Authorization": "Bearer " + dados["access_token"]}}
    return resultado

def test_token_sem_assinatura_e_recusado(cliente):
    token = jwt.encode({"sub": "1", "perfil": "admin", "iss": "helpdesk-ti"}, None, algorithm="none")
    for caminho in ("/usuarios", "/ativos", "/chamados", "/notificacoes"):
        resposta = cliente.get(caminho, headers={"Authorization": f"Bearer {token}"})
        assert resposta.status_code == 401, (caminho, resposta.text)

def test_requisicao_grande_e_recusada(cliente, contas):
    corpo = '{"titulo":"' + "x" * 70000 + '"}'
    resposta = cliente.post("/chamados", content=corpo,
                           headers={**contas["ana"]["headers"], "Content-Type": "application/json"})
    assert resposta.status_code == 413, resposta.text

def test_nao_pode_abrir_chamado_por_outra_pessoa(cliente, contas):
    resposta = cliente.post("/chamados", headers=contas["ana"]["headers"],
                           json={"titulo": "Chamado forjado", "descricao": "Teste de permissões",
                                 "prioridade": "baixa", "solicitante_id": contas["bruno"]["id"]})
    assert resposta.status_code == 422, resposta.text

def test_nao_pode_falsificar_autor_do_comentario(cliente, contas):
    resposta = cliente.post("/chamados", headers=contas["ana"]["headers"],
                           json={"titulo": "Chamado de autorização",
                                 "descricao": "Verificar quem envia comentários", "prioridade": "baixa"})
    assert resposta.status_code == 201, resposta.text
    cid = resposta.json()["id"]
    resposta = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["ana"]["headers"],
                           json={"texto": "Comentário forjado", "autor_id": contas["carla"]["id"]})
    assert resposta.status_code == 422, resposta.text

def test_lista_de_usuarios_nao_mostra_emails(cliente, contas):
    resposta = cliente.get("/usuarios", headers=contas["ana"]["headers"])
    assert resposta.status_code == 200
    assert resposta.json() and all("email" not in dado for dado in resposta.json())

def test_senha_fraca_e_recusada(cliente, contas):
    email = f"teste-{uuid.uuid4().hex[:10]}@empresa.com"
    resposta = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                           json={"nome": "Usuário Teste", "email": email,
                                 "perfil": "solicitante", "senha": "apenasletras"})
    assert resposta.status_code == 422, resposta.text

def test_iniciar_atendimento_exige_tecnico(cliente, contas):
    resposta = cliente.post("/chamados", headers=contas["ana"]["headers"],
                           json={"titulo": "Solicitação nova", "descricao": "Sem técnico atribuído",
                                 "prioridade": "media"})
    assert resposta.status_code == 201, resposta.text
    cid = resposta.json()["id"]
    resposta = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"],
                            json={"status": "em_atendimento"})
    assert resposta.status_code == 422, resposta.text

def test_bloqueio_de_tentativas_de_login(cliente):
    email = f"desconhecido-{uuid.uuid4().hex[:12]}@empresa.com"
    for _ in range(5):
        resposta = cliente.post("/auth/login", json={"email": email, "senha": "senha-errada"})
        assert resposta.status_code == 401, resposta.text
    resposta = cliente.post("/auth/login", json={"email": email, "senha": "senha-errada"})
    assert resposta.status_code == 429, resposta.text

def test_cabecalhos_e_protecao_xss(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "script-src 'self'" in resposta.headers["content-security-policy"]
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-frame-options"] == "DENY"
    script = cliente.get("/app.js")
    assert script.status_code == 200 and "const esc =" in script.text
