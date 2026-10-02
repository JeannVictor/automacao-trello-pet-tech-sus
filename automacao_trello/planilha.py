import os
import re
import urllib.parse
from pathlib import Path

import pandas as pd
import requests


def xls_to_tsv(url_original):
    match_id = re.search(r"/d/([^/]+)/edit", url_original)
    match_gid = re.search(r"[?&]gid=([^&#]+)", url_original)

    if not match_id:
        raise ValueError("Não foi possível encontrar o ID da planilha.")

    if not match_gid:
        raise ValueError("Não foi possível encontrar o GID da aba.")

    spreadsheet_id = match_id.group(1)
    gid = match_gid.group(1)

    return (
        "https://docs.google.com/spreadsheets/d/"
        f"{spreadsheet_id}/export?format=tsv&gid={gid}"
    )


def download_tsv(url, pasta_destino):
    pasta_destino = Path(pasta_destino)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    resposta = requests.get(url, stream=True, timeout=60)
    resposta.raise_for_status()

    nome_arquivo = None
    content_disp = resposta.headers.get("Content-Disposition", "")

    for parte in content_disp.split(";"):
        if "filename=" in parte:
            nome_arquivo = parte.split("filename=", 1)[1].strip('" ')
            break

    if not nome_arquivo:
        url_decodificada = urllib.parse.unquote(url)
        nome_arquivo = os.path.basename(
            urllib.parse.urlparse(url_decodificada).path
        )

    if not nome_arquivo or nome_arquivo == "export":
        nome_arquivo = "Sprint_Atual.tsv"

    if not nome_arquivo.lower().endswith(".tsv"):
        nome_arquivo = f"{nome_arquivo}.tsv"

    caminho_completo = pasta_destino / nome_arquivo

    with caminho_completo.open("wb") as arquivo:
        for pedaco in resposta.iter_content(chunk_size=8192):
            if pedaco:
                arquivo.write(pedaco)

    print(f"Planilha baixada temporariamente: {nome_arquivo}")
    return caminho_completo


def limpeza_tsv(caminho_arquivo):
    caminho_arquivo = Path(caminho_arquivo)

    with caminho_arquivo.open(encoding="utf-8") as arquivo:
        linhas = arquivo.readlines()

    idx_header = None

    for indice, linha in enumerate(linhas):
        if linha.strip().startswith("ID\tTipo"):
            idx_header = indice
            break

    if idx_header is None:
        raise ValueError(
            f"Cabeçalho 'ID\\tTipo' não encontrado em {caminho_arquivo.name}."
        )

    ultima_linha = None

    for indice in range(idx_header + 1, len(linhas)):
        if linhas[indice].lstrip().startswith("US"):
            ultima_linha = indice

    if ultima_linha is None:
        raise ValueError(
            f"Nenhuma linha iniciada por 'US' foi encontrada em "
            f"{caminho_arquivo.name}."
        )

    linhas_uteis = linhas[idx_header:ultima_linha + 1]

    with caminho_arquivo.open("w", encoding="utf-8") as arquivo:
        arquivo.writelines(linhas_uteis)

    print("Limpeza da planilha concluída.")
    return caminho_arquivo


def filtrar_por_time(caminho_arquivo, numero_time, pasta_destino):
    caminho_arquivo = Path(caminho_arquivo)
    pasta_destino = Path(pasta_destino)
    df = pd.read_csv(caminho_arquivo, sep="\t")
    df.columns = df.columns.str.strip()

    coluna_alvo = f"Estimativa Parcial  (Time {numero_time})"

    if coluna_alvo not in df.columns:
        coluna_alvo = f"Estimativa Parcial (Time {numero_time})"

    if coluna_alvo not in df.columns:
        for coluna in df.columns:
            if f"Time {numero_time}" in coluna and "Estimativa" in coluna:
                coluna_alvo = coluna
                break

    if coluna_alvo not in df.columns:
        raise ValueError(
            f"Coluna 'Estimativa Parcial (Time {numero_time})' não encontrada. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    df[coluna_alvo] = pd.to_numeric(df[coluna_alvo], errors="coerce")
    df_filtrado = df[df[coluna_alvo] > 0].copy()

    nome_base = caminho_arquivo.stem
    caminho_filtrado = pasta_destino / f"{nome_base}_time_{numero_time}.tsv"
    df_filtrado.to_csv(
        caminho_filtrado,
        sep="\t",
        index=False,
        encoding="utf-8",
    )

    print(
        f"Filtro do Time {numero_time} concluído: "
        f"{len(df_filtrado)} história(s)."
    )
    return caminho_filtrado


def historias_to_dict(caminho_arquivo):
    df = pd.read_csv(caminho_arquivo, sep="\t")
    df.columns = df.columns.str.strip()

    return df.to_dict(orient="records")
