"""Cria apenas usuários de demonstração no banco deste serviço."""
import os
from sqlalchemy.orm import Session
from app.usuarios import servico
from app.usuarios.esquemas import UsuarioCriar

def carregar(db: Session) -> None:
    if servico.listar(db):
        return
    senha = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")
    contas = [
        ("Admin TI", "admin@empresa.com", "admin"),
        ("Ana Souza", "ana@empresa.com", "solicitante"),
        ("Bruno Lima", "bruno@empresa.com", "solicitante"),
        ("Carla Dias", "carla@empresa.com", "tecnico"),
        ("Diego Rocha", "diego@empresa.com", "tecnico"),
    ]
    for nome, email, perfil in contas:
        servico.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=senha))
