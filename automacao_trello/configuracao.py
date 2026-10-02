import json
import os
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent.parent

CORES_PADRAO_TIME_1 = {
    "gat_4": {
        "us": "green_light",
        "tus": "green_dark",
    },
    "historia_time_1": {
        "us": "yellow",
        "tus": "yellow_dark",
    },
    "reuniao_orientador": {
        "us": "red",
        "tus": "red_dark",
    },
    "atualizar_diariamente": {
        "us": "red",
        "tus": "red_dark",
    },
}


def caminho_configuracao_membros():
    caminho_personalizado = os.getenv("MEMBROS_CONFIG_PATH")

    if caminho_personalizado:
        return Path(caminho_personalizado).expanduser()

    return PASTA_PROJETO / "config" / "membros.json"


def carregar_membros_por_time():
    caminho = caminho_configuracao_membros()

    if not caminho.exists():
        raise ValueError(
            f"Configuração de membros não encontrada em '{caminho}'. "
            "Copie config/membros.example.json para config/membros.json "
            "e preencha os dados locais."
        )

    with caminho.open(encoding="utf-8") as arquivo:
        membros_por_time = json.load(arquivo)

    if not isinstance(membros_por_time, dict):
        raise ValueError("config/membros.json deve conter um objeto JSON.")

    return membros_por_time
