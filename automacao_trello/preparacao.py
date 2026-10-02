import re
import secrets

from automacao_trello.configuracao import CORES_PADRAO_TIME_1
from automacao_trello.membros import buscar_ids_responsaveis
from automacao_trello.texto import normalizar_texto


def definir_cores_historia(historia, numero_time):
    id_historia = str(historia.get("ID", "")).strip().upper()
    responsaveis = normalizar_texto(historia.get("Time/Responsável", ""))
    observacao = normalizar_texto(historia.get("Observação", ""))
    titulo = normalizar_texto(historia.get("Título", ""))

    if id_historia == "US-1401":
        return CORES_PADRAO_TIME_1["atualizar_diariamente"]

    if "gat-4" in responsaveis or "gat 4" in responsaveis:
        return CORES_PADRAO_TIME_1["gat_4"]

    eh_recorrente = "atividade recorrente" in observacao
    eh_reuniao_com_orientador = eh_recorrente and (
        titulo.startswith("orientar ")
        or "reuniao com orientador" in titulo
        or "reuniao de orientacao" in titulo
    )

    if numero_time == 1 and eh_reuniao_com_orientador:
        return CORES_PADRAO_TIME_1["reuniao_orientador"]

    return CORES_PADRAO_TIME_1["historia_time_1"]


def reservar_labels_tus(labels_existentes, quantidade, numeros_reservados):
    if quantidade == 0:
        return []

    labels_por_numero = {}
    todos_numeros = set(numeros_reservados)

    for label in labels_existentes:
        match = re.fullmatch(r"TUS-(\d{4})", label.get("name", "").upper())

        if not match:
            continue

        numero = int(match.group(1))
        todos_numeros.add(numero)

        if label.get("uses", 0) == 0 and numero not in numeros_reservados:
            labels_por_numero[numero] = label

    for primeiro_numero in sorted(labels_por_numero):
        bloco = list(range(primeiro_numero, primeiro_numero + quantidade))

        if all(numero in labels_por_numero for numero in bloco):
            numeros_reservados.update(bloco)
            return [
                {
                    "name": f"TUS-{numero:04d}",
                    "id": labels_por_numero[numero].get("id"),
                }
                for numero in bloco
            ]

    primeiro_numero = max(todos_numeros, default=999) + 1

    if primeiro_numero + quantidade - 1 > 9999:
        for _ in range(9000):
            candidato = 1000 + secrets.randbelow(9000)
            bloco = range(candidato, candidato + quantidade)

            if candidato + quantidade - 1 <= 9999 and all(
                numero not in todos_numeros for numero in bloco
            ):
                primeiro_numero = candidato
                break
        else:
            raise ValueError(
                "Não foi possível encontrar uma sequência livre de labels TUS."
            )

    bloco = list(range(primeiro_numero, primeiro_numero + quantidade))
    numeros_reservados.update(bloco)

    return [
        {"name": f"TUS-{numero:04d}", "id": None}
        for numero in bloco
    ]


def preparar_historias_para_trello(
    historias,
    numero_time,
    membros_quadro,
    labels_existentes,
    membros_por_time,
):
    labels_por_nome = {
        label.get("name", "").upper(): label
        for label in labels_existentes
        if label.get("name")
    }
    resultado = []
    numeros_reservados = set()

    for historia in historias:
        historia_preparada = historia.copy()
        ids_membros, pendencias = buscar_ids_responsaveis(
            historia.get("Time/Responsável", ""),
            numero_time,
            membros_quadro,
            membros_por_time,
        )
        id_historia = str(historia.get("ID", "")).strip().upper()
        label_historia_existente = labels_por_nome.get(id_historia)
        cores = definir_cores_historia(historia, numero_time)
        labels_tus = reservar_labels_tus(
            labels_existentes,
            len(historia.get("Tarefas", [])),
            numeros_reservados,
        )
        tarefas_trello = []

        for tarefa, label_tus in zip(historia.get("Tarefas", []), labels_tus):
            tarefas_trello.append(
                {
                    "Título": tarefa,
                    "Labels": [id_historia, label_tus["name"]],
                    "ID da label TUS existente": label_tus["id"],
                    "Cor da TUS": cores["tus"],
                }
            )

        historia_preparada["Cor da US"] = cores["us"]
        historia_preparada["ID da label US existente"] = (
            label_historia_existente.get("id")
            if label_historia_existente
            else None
        )
        historia_preparada["IDs dos Membros no Trello"] = ids_membros
        historia_preparada["Pendências de Membros"] = pendencias
        historia_preparada["Tarefas no Trello"] = tarefas_trello
        resultado.append(historia_preparada)

    return resultado
