"""Cria equipamentos de demonstração no banco de Inventário."""
from sqlalchemy.orm import Session
from app.inventario import servico
from app.inventario.esquemas import AtivoCriar

def carregar(db: Session) -> None:
    if servico.listar(db):
        return
    dados = [
        ("PAT-0001", "computador", "Desktop Dell OptiPlex", "Financeiro"),
        ("PAT-0002", "impressora", "Impressora HP LaserJet", "RH"),
        ("PAT-0003", "notebook", "Notebook Lenovo ThinkPad", "TI"),
    ]
    for patrimonio, tipo, descricao, setor in dados:
        servico.criar(db, AtivoCriar(patrimonio=patrimonio, tipo=tipo, descricao=descricao, setor=setor))
