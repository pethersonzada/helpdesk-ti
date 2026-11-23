"""Executar apenas depois de `docker compose stop inventario`."""
import os
import httpx

BASE_URL = os.getenv("TEST_GATEWAY_URL", "http://127.0.0.1:8000")
SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")

def test_erro_claro_e_servicos_independentes():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as cliente:
        login = cliente.post("/auth/login", json={"email": "ana@empresa.com", "senha": SENHA})
        assert login.status_code == 200, login.text
        cabecalho = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert cliente.get("/usuarios", headers=cabecalho).status_code == 200
        assert cliente.get("/chamados", headers=cabecalho).status_code == 200
        assert cliente.get("/chamados/painel", headers=cabecalho).status_code == 200

        resposta = cliente.post("/chamados", headers=cabecalho,
                                json={"titulo": "Falha controlada no inventário",
                                      "descricao": "A API deve responder sem travar.",
                                      "prioridade": "alta", "ativo_id": 1})
        assert resposta.status_code == 503, resposta.text
        assert "indisponível" in resposta.json()["detail"]
        # Chamados sem equipamento continuam sendo abertos.
        sem_equipamento = cliente.post("/chamados", headers=cabecalho,
                                      json={"titulo": "Solicitação sem equipamento",
                                            "descricao": "Não depende do inventário.",
                                            "prioridade": "baixa"})
        assert sem_equipamento.status_code == 201, sem_equipamento.text
