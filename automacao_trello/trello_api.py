import os
import re
from time import sleep

import requests


def credenciais_trello():
    api_key = os.getenv("TRELLO_API_KEY")
    token = os.getenv("TRELLO_TOKEN")

    if not api_key or not token:
        raise ValueError(
            "TRELLO_API_KEY e TRELLO_TOKEN precisam estar definidos no arquivo .env."
        )

    return api_key, token


def requisicao_trello(metodo, url, **argumentos):
    maximo_tentativas = 5

    for tentativa in range(maximo_tentativas):
        resposta = requests.request(metodo, url, **argumentos)

        if resposta.status_code != 429:
            return resposta

        if tentativa == maximo_tentativas - 1:
            return resposta

        retry_after = resposta.headers.get("Retry-After")

        try:
            tempo_espera = float(retry_after)
        except (TypeError, ValueError):
            tempo_espera = 2 ** tentativa

        tempo_espera = min(max(tempo_espera, 1), 60)
        print(
            "Limite temporário da API do Trello atingido. "
            f"Nova tentativa em {tempo_espera:g} segundo(s)..."
        )
        sleep(tempo_espera)


def pegar_id_quadro(link_quadro):
    match = re.search(r"trello\.com/b/([^/]+)", link_quadro)

    if not match:
        raise ValueError("Não foi possível encontrar o identificador do quadro.")

    identificador_quadro = match.group(1)
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "GET",
        f"https://api.trello.com/1/boards/{identificador_quadro}",
        params={"key": api_key, "token": token},
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()["id"]


def buscar_membros_quadro(id_quadro):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "GET",
        f"https://api.trello.com/1/boards/{id_quadro}/members",
        params={"key": api_key, "token": token},
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def buscar_labels_quadro(id_quadro):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "GET",
        f"https://api.trello.com/1/boards/{id_quadro}/labels",
        params={
            "key": api_key,
            "token": token,
            "limit": 1000,
            "fields": "all",
        },
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def buscar_listas_quadro(id_quadro):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "GET",
        f"https://api.trello.com/1/boards/{id_quadro}/lists",
        params={
            "key": api_key,
            "token": token,
            "filter": "open",
            "fields": "id,name",
        },
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def buscar_cards_quadro(id_quadro, incluir_arquivados=False):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "GET",
        f"https://api.trello.com/1/boards/{id_quadro}/cards",
        params={
            "key": api_key,
            "token": token,
            "filter": "all" if incluir_arquivados else "open",
            "fields": "id,name,desc,idList,idLabels,idMembers,closed",
        },
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def obter_ou_criar_label(id_quadro, nome, cor, labels_por_nome):
    api_key, token = credenciais_trello()
    nome_normalizado = nome.strip().upper()
    label = labels_por_nome.get(nome_normalizado)

    if label:
        if label.get("color") != cor:
            resposta = requisicao_trello(
                "PUT",
                f"https://api.trello.com/1/labels/{label['id']}",
                params={"key": api_key, "token": token},
                data={"color": cor},
                timeout=30,
            )
            resposta.raise_for_status()
            label = {**label, **resposta.json()}
            labels_por_nome[nome_normalizado] = label

        return label

    resposta = requisicao_trello(
        "POST",
        "https://api.trello.com/1/labels",
        params={"key": api_key, "token": token},
        data={
            "idBoard": id_quadro,
            "name": nome_normalizado,
            "color": cor,
        },
        timeout=30,
    )
    resposta.raise_for_status()
    label = resposta.json()
    labels_por_nome[nome_normalizado] = label

    return label


def criar_card_trello(
    id_lista,
    titulo,
    descricao="",
    ids_labels=None,
    ids_membros=None,
):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "POST",
        "https://api.trello.com/1/cards",
        params={"key": api_key, "token": token},
        data={
            "idList": id_lista,
            "name": titulo,
            "desc": descricao,
            "idLabels": ",".join(ids_labels or []),
            "idMembers": ",".join(ids_membros or []),
        },
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def atualizar_card_trello(
    id_card,
    id_lista,
    titulo,
    descricao="",
    ids_labels=None,
    ids_membros=None,
):
    api_key, token = credenciais_trello()
    resposta = requisicao_trello(
        "PUT",
        f"https://api.trello.com/1/cards/{id_card}",
        params={"key": api_key, "token": token},
        data={
            "idList": id_lista,
            "name": titulo,
            "desc": descricao,
            "idLabels": ",".join(ids_labels or []),
            "idMembers": ",".join(ids_membros or []),
            "closed": "false",
        },
        timeout=30,
    )
    resposta.raise_for_status()

    return resposta.json()


def resumir_erro_trello(erro):
    resposta = getattr(erro, "response", None)

    if resposta is None:
        return "não foi possível se comunicar com a API do Trello"

    detalhe = resposta.text.strip().replace("\n", " ")

    if detalhe:
        return f"status {resposta.status_code}: {detalhe[:300]}"

    return f"status {resposta.status_code}"
