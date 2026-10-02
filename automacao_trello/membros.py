import re

from automacao_trello.texto import normalizar_texto


def extrair_trecho_time(texto_responsaveis, numero_time):
    texto_responsaveis = str(texto_responsaveis)
    match = re.search(
        rf"\btime\s*{numero_time}\b(.*?)(?=\btime\s*[123]\b|$)",
        texto_responsaveis,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(0).strip()


def buscar_ids_responsaveis(
    texto_responsaveis,
    numero_time,
    membros_quadro,
    membros_por_time,
):
    texto_normalizado = normalizar_texto(texto_responsaveis)
    todos_ids_membros = [membro["id"] for membro in membros_quadro]
    ids_membros_quadro = set(todos_ids_membros)

    if "gat-4" in texto_normalizado or "gat 4" in texto_normalizado:
        return todos_ids_membros, []

    trecho_time = extrair_trecho_time(texto_responsaveis, numero_time)
    trecho_normalizado = normalizar_texto(trecho_time)

    if not trecho_time:
        return [], [
            f"Time {numero_time} não encontrado em: {texto_responsaveis}"
        ]

    somente_time = re.fullmatch(
        rf"time\s*{numero_time}\s*[-:]*",
        trecho_normalizado,
    )

    if somente_time:
        return todos_ids_membros, []

    ids_encontrados = []
    pendencias = []
    membros_configurados = membros_por_time.get(str(numero_time), [])

    for membro in membros_configurados:
        apelidos = membro.get("apelidos", []) + [
            membro.get("nome", ""),
            membro.get("username", ""),
        ]
        encontrou = any(
            apelido and re.search(
                rf"(?<!\w){re.escape(normalizar_texto(apelido))}(?!\w)",
                trecho_normalizado,
            )
            for apelido in apelidos
        )

        if encontrou and membro.get("id") in ids_membros_quadro:
            ids_encontrados.append(membro["id"])

    if numero_time == 3 and "pagliares" in trecho_normalizado:
        contas_pagliares = [
            membro
            for membro in membros_configurados
            if "pagliares" in normalizar_texto(membro.get("nome", ""))
        ]

        if len(contas_pagliares) > 1 and not ids_encontrados:
            pendencias.append(
                "Há mais de uma conta configurada para Pagliares. "
                "Use um apelido ou username específico em config/membros.json."
            )

    if not ids_encontrados and not pendencias:
        pendencias.append(f"Nenhum membro reconhecido no trecho: {trecho_time}")

    return list(dict.fromkeys(ids_encontrados)), pendencias
