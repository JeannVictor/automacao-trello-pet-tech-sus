import re
import unicodedata

import pandas as pd


def extrair_tarefas(historias):
    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto))
        texto = "".join(
            caractere
            for caractere in texto
            if not unicodedata.combining(caractere)
        )

        texto = texto.lower()
        texto = texto.replace("✔", " ")
        texto = texto.replace("🛠", " ")
        texto = re.sub(r"\s+", " ", texto)

        return texto.strip(" :-\t")

    def encontrar_coluna_criterios(historia):
        for coluna in historia:
            coluna_normalizada = normalizar(coluna)

            if "criterio" in coluna_normalizada and "aceitacao" in coluna_normalizada:
                return coluna

        return None

    def encontrar_secao_tarefas(texto):
        padroes_inicio = (
            (
                r"🛠\s*"
                r"(?:poss[ií]ve\w*\s+)?"
                r"tarefas"
                r"(?:\s*\([^\n]*?\))?"
                r"\s*:?\s*"
            ),
            (
                r"(?m)^\s*"
                r"(?:poss[ií]ve\w*\s+)?"
                r"tarefas"
                r"(?:\s*\([^\n]*?\))?"
                r"\s*:?\s*$"
            ),
            r"\s{2,}tarefas\s*:\s*",
        )

        inicios_encontrados = []

        for padrao in padroes_inicio:
            resultado = re.search(padrao, texto, flags=re.IGNORECASE)

            if resultado:
                inicios_encontrados.append(resultado)

        if not inicios_encontrados:
            return ""

        inicio = min(inicios_encontrados, key=lambda resultado: resultado.start())
        secao = texto[inicio.end():]

        prefixo_secao = (
            r"(?:^|\n|\s{2,})"
            r"\s*(?:[-•]\s*)?"
            r"(?:✔|🛠)?\s*"
        )

        padroes_fim = (
            prefixo_secao + r"crit[eé]rios?\s+de\s+aceita[cç][aã]o\b",
            prefixo_secao + r"diretriz\b",
            prefixo_secao + r"sprint\s+review\b",
            prefixo_secao + r"sprint\s+retrospective\b",
            prefixo_secao + r"maiores\s+informa[cç][oõ]es\b",
            prefixo_secao + r"link\s*:",
            prefixo_secao + r"obs+erva[cç][aã]o\s*:",
        )

        finais_encontrados = []

        for padrao in padroes_fim:
            resultado = re.search(padrao, secao, flags=re.IGNORECASE)

            if resultado:
                finais_encontrados.append(resultado.start())

        if finais_encontrados:
            secao = secao[:min(finais_encontrados)]

        return secao.strip()

    def extrair_com_quebras_de_linha(secao):
        tarefas = []
        modo_numerado = False
        ignorando_detalhes = False

        for linha_original in secao.splitlines():
            linha = linha_original.strip().strip('"').strip()

            if not linha or linha == ".":
                continue

            if normalizar(linha).startswith("objetivo"):
                ignorando_detalhes = True
                continue

            tarefa_numerada = re.match(r"^\s*\d+\s*[.)-]\s*(.+)", linha)

            if tarefa_numerada:
                if tarefas and tarefas[-1].endswith(":") and not modo_numerado:
                    ignorando_detalhes = True
                    continue

                tarefa = tarefa_numerada.group(1).strip()
                tarefas.append(tarefa)
                modo_numerado = True
                ignorando_detalhes = True
                continue

            tarefa_com_marcador = re.match(r"^\s*[-•]\s*(.+)", linha)

            if tarefa_com_marcador:
                tarefa = tarefa_com_marcador.group(1).strip()
                tarefas.append(tarefa)
                modo_numerado = False
                ignorando_detalhes = False
                continue

            if ignorando_detalhes:
                continue

            linha_normalizada = normalizar(linha)

            if linha_normalizada.startswith("http"):
                continue

            if linha_normalizada.startswith("slides ("):
                continue

            tarefas.append(linha)

        return tarefas

    def extrair_sem_quebras_de_linha(secao):
        if not re.match(r"^\s*[-•]", secao):
            marcadores_numerados = list(
                re.finditer(r"(?:^|\s{2,})(\d+)\s*[.)]\s+", secao)
            )

            if marcadores_numerados:
                tarefas_numeradas = []

                for indice, marcador in enumerate(marcadores_numerados):
                    inicio = marcador.end()

                    if indice + 1 < len(marcadores_numerados):
                        fim = marcadores_numerados[indice + 1].start()
                    else:
                        fim = len(secao)

                    tarefa = secao[inicio:fim].strip()
                    tarefa = re.split(
                        r"\s+objetivo\s*:",
                        tarefa,
                        maxsplit=1,
                        flags=re.IGNORECASE,
                    )[0].strip()

                    if tarefa:
                        tarefas_numeradas.append(tarefa)

                if tarefas_numeradas:
                    return tarefas_numeradas

        partes = [
            parte.strip()
            for parte in re.split(r"\s+-\s+", secao)
            if parte.strip()
        ]

        tarefas = []
        inicios_sem_verbo = {
            "inspecao",
            "criacao",
            "preparacao",
            "correcao",
            "leitura",
            "entrega",
            "solicitacao",
            "link",
        }

        for parte in partes:
            parte = re.sub(r"^\s*[-•]\s*", "", parte).strip()
            detalhe_numerado = re.search(r"\s+\d+\s*[.)]\s+", parte)

            if detalhe_numerado:
                antes_dos_detalhes = parte[:detalhe_numerado.start()].rstrip()

                if antes_dos_detalhes.endswith(":"):
                    parte = antes_dos_detalhes

            if not parte or parte == ".":
                continue

            primeira_palavra = normalizar(parte).split(" ", 1)[0]
            comeca_com_verbo = bool(
                re.match(r"^[a-z]+(?:ar|er|ir)$", primeira_palavra)
            )
            parece_nova_tarefa = parte[0].isupper() and (
                comeca_com_verbo or primeira_palavra in inicios_sem_verbo
            )

            if not tarefas or parece_nova_tarefa:
                tarefas.append(parte)
            else:
                tarefas[-1] = f"{tarefas[-1]} - {parte}"

        return tarefas

    resultado = []

    for historia in historias:
        coluna_criterios = encontrar_coluna_criterios(historia)

        if coluna_criterios is None:
            raise ValueError("Coluna 'Critério de Aceitação' não encontrada.")

        texto = historia.get(coluna_criterios)

        if pd.isna(texto):
            tarefas = []
        else:
            secao = encontrar_secao_tarefas(str(texto))

            if "\n" in secao:
                tarefas = extrair_com_quebras_de_linha(secao)
            elif secao:
                tarefas = extrair_sem_quebras_de_linha(secao)
            else:
                tarefas = []

        tarefas_unicas = []
        tarefas_vistas = set()

        for tarefa in tarefas:
            chave = normalizar(tarefa)

            if chave and chave not in tarefas_vistas:
                tarefas_unicas.append(tarefa)
                tarefas_vistas.add(chave)

        historia_formatada = historia.copy()
        historia_formatada["Tarefas"] = tarefas_unicas
        resultado.append(historia_formatada)

    return resultado
