import requests

from automacao_trello.texto import limpar_valor, normalizar_texto
from automacao_trello.trello_api import (
    atualizar_card_trello,
    buscar_cards_quadro,
    buscar_labels_quadro,
    buscar_listas_quadro,
    criar_card_trello,
    obter_ou_criar_label,
    resumir_erro_trello,
)


def encontrar_lista(listas, nome_procurado):
    nome_normalizado = normalizar_texto(nome_procurado)
    listas_encontradas = [
        lista
        for lista in listas
        if normalizar_texto(lista.get("name", "")).startswith(nome_normalizado)
    ]

    if not listas_encontradas:
        raise ValueError(
            f"A lista '{nome_procurado}' não foi encontrada no quadro."
        )

    if len(listas_encontradas) > 1:
        nomes = [lista["name"] for lista in listas_encontradas]
        raise ValueError(
            f"Mais de uma lista corresponde a '{nome_procurado}': {nomes}"
        )

    return listas_encontradas[0]


def montar_descricao_historia(historia):
    descricao = limpar_valor(historia.get("Descrição"))
    criterios = limpar_valor(historia.get("Critério de Aceitação"))

    return "\n\n".join(
        parte
        for parte in (descricao, criterios)
        if parte
    )


def encontrar_card_historia(cards, id_label_us, nomes_labels_por_id):
    for card in sorted(cards, key=lambda item: item.get("closed", False)):
        if id_label_us not in card.get("idLabels", []):
            continue

        possui_label_tus = any(
            nomes_labels_por_id.get(id_label, "").startswith("TUS-")
            for id_label in card.get("idLabels", [])
        )

        if not possui_label_tus:
            return card

    return None


def encontrar_card_tarefa(cards, id_label_us, titulo, nomes_labels_por_id):
    titulo_normalizado = normalizar_texto(titulo)

    for card in sorted(cards, key=lambda item: item.get("closed", False)):
        if id_label_us not in card.get("idLabels", []):
            continue

        possui_label_tus = any(
            nomes_labels_por_id.get(id_label, "").startswith("TUS-")
            for id_label in card.get("idLabels", [])
        )

        if (
            possui_label_tus
            and normalizar_texto(card.get("name", "")) == titulo_normalizado
        ):
            return card

    return None


def montar_quadro_trello(id_quadro, historias, atualizar=False):
    listas = buscar_listas_quadro(id_quadro)
    lista_historias = encontrar_lista(listas, "User Stories Priorizadas")
    lista_tarefas = encontrar_lista(listas, "Tarefas Planejadas")
    labels_existentes = buscar_labels_quadro(id_quadro)
    cards = buscar_cards_quadro(
        id_quadro,
        incluir_arquivados=atualizar,
    )
    labels_por_nome = {
        label.get("name", "").strip().upper(): label
        for label in labels_existentes
        if label.get("name")
    }
    nomes_labels_por_id = {
        label["id"]: label.get("name", "").strip().upper()
        for label in labels_existentes
    }
    relatorio = {
        "historias_criadas": [],
        "historias_atualizadas": [],
        "historias_ignoradas": [],
        "tarefas_criadas": [],
        "tarefas_atualizadas": [],
        "tarefas_ignoradas": [],
        "avisos": [],
        "erros": [],
    }

    for historia in historias:
        id_historia = limpar_valor(historia.get("ID")).upper()
        titulo_historia = limpar_valor(historia.get("Título"))
        pendencias = historia.get("Pendências de Membros", [])

        if not id_historia or not titulo_historia:
            relatorio["erros"].append(
                "Uma história sem ID ou título foi ignorada."
            )
            continue

        if pendencias:
            relatorio["erros"].append(
                f"{id_historia}: {'; '.join(pendencias)}"
            )
            continue

        try:
            label_us = obter_ou_criar_label(
                id_quadro,
                id_historia,
                historia["Cor da US"],
                labels_por_nome,
            )
            nomes_labels_por_id[label_us["id"]] = id_historia
            card_historia = encontrar_card_historia(
                cards,
                label_us["id"],
                nomes_labels_por_id,
            )

            if card_historia and not atualizar:
                relatorio["historias_ignoradas"].append(id_historia)
                tarefas_ignoradas = [
                    tarefa["Título"]
                    for tarefa in historia.get("Tarefas no Trello", [])
                ]
                relatorio["tarefas_ignoradas"].extend(tarefas_ignoradas)
                relatorio["avisos"].append(
                    f"{id_historia} já possui um card aberto. "
                    f"A história e suas {len(tarefas_ignoradas)} tarefa(s) "
                    "não foram alteradas."
                )
                continue

            dados_historia = {
                "id_lista": lista_historias["id"],
                "titulo": titulo_historia,
                "descricao": montar_descricao_historia(historia),
                "ids_labels": [label_us["id"]],
                "ids_membros": historia["IDs dos Membros no Trello"],
            }

            if card_historia:
                card_atualizado = atualizar_card_trello(
                    card_historia["id"],
                    **dados_historia,
                )
                cards.remove(card_historia)
                cards.append(card_atualizado)
                relatorio["historias_atualizadas"].append(id_historia)
            else:
                card_criado = criar_card_trello(**dados_historia)
                cards.append(card_criado)
                relatorio["historias_criadas"].append(id_historia)

            for tarefa in historia.get("Tarefas no Trello", []):
                titulo_tarefa = limpar_valor(tarefa.get("Título"))
                nome_label_tus = tarefa["Labels"][1]
                card_tarefa = encontrar_card_tarefa(
                    cards,
                    label_us["id"],
                    titulo_tarefa,
                    nomes_labels_por_id,
                )

                if card_tarefa and not atualizar:
                    relatorio["tarefas_ignoradas"].append(titulo_tarefa)
                    continue

                ids_labels_tarefa = [label_us["id"]]

                if card_tarefa:
                    labels_tus_atuais = [
                        id_label
                        for id_label in card_tarefa.get("idLabels", [])
                        if nomes_labels_por_id.get(id_label, "").startswith("TUS-")
                    ]

                    if labels_tus_atuais:
                        id_label_tus_atual = labels_tus_atuais[0]
                        nome_label_tus_atual = nomes_labels_por_id[
                            id_label_tus_atual
                        ]
                        obter_ou_criar_label(
                            id_quadro,
                            nome_label_tus_atual,
                            tarefa["Cor da TUS"],
                            labels_por_nome,
                        )
                        ids_labels_tarefa.append(id_label_tus_atual)
                    else:
                        label_tus = obter_ou_criar_label(
                            id_quadro,
                            nome_label_tus,
                            tarefa["Cor da TUS"],
                            labels_por_nome,
                        )
                        nomes_labels_por_id[label_tus["id"]] = nome_label_tus
                        ids_labels_tarefa.append(label_tus["id"])

                    card_atualizado = atualizar_card_trello(
                        card_tarefa["id"],
                        lista_tarefas["id"],
                        titulo_tarefa,
                        ids_labels=ids_labels_tarefa,
                        ids_membros=historia["IDs dos Membros no Trello"],
                    )
                    cards.remove(card_tarefa)
                    cards.append(card_atualizado)
                    relatorio["tarefas_atualizadas"].append(titulo_tarefa)
                else:
                    label_tus = obter_ou_criar_label(
                        id_quadro,
                        nome_label_tus,
                        tarefa["Cor da TUS"],
                        labels_por_nome,
                    )
                    nomes_labels_por_id[label_tus["id"]] = nome_label_tus
                    ids_labels_tarefa.append(label_tus["id"])
                    card_criado = criar_card_trello(
                        lista_tarefas["id"],
                        titulo_tarefa,
                        ids_labels=ids_labels_tarefa,
                        ids_membros=historia["IDs dos Membros no Trello"],
                    )
                    cards.append(card_criado)
                    relatorio["tarefas_criadas"].append(titulo_tarefa)
        except requests.RequestException as erro:
            relatorio["erros"].append(
                f"{id_historia}: {resumir_erro_trello(erro)}"
            )

    return relatorio
