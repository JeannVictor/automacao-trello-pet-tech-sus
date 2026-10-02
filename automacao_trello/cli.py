import json
import sys
from tempfile import TemporaryDirectory

import requests
from dotenv import load_dotenv

from automacao_trello.configuracao import (
    PASTA_PROJETO,
    carregar_membros_por_time,
)
from automacao_trello.planilha import (
    download_tsv,
    filtrar_por_time,
    historias_to_dict,
    limpeza_tsv,
    xls_to_tsv,
)
from automacao_trello.preparacao import preparar_historias_para_trello
from automacao_trello.quadro import montar_quadro_trello
from automacao_trello.tarefas import extrair_tarefas
from automacao_trello.texto import normalizar_texto
from automacao_trello.trello_api import (
    buscar_labels_quadro,
    buscar_membros_quadro,
    pegar_id_quadro,
    resumir_erro_trello,
)


def exibir_previa(historias_preparadas, atualizar):
    print("\nPrévia do que será enviado ao Trello:")

    for historia in historias_preparadas:
        print(
            f"- {historia['ID']} | {historia['Título']} | "
            f"{historia['Cor da US']} | "
            f"{len(historia['Tarefas no Trello'])} tarefa(s)"
        )

        for pendencia in historia["Pendências de Membros"]:
            print(f"  PENDÊNCIA: {pendencia}")

    if atualizar:
        print(
            "\nModo --atualizar ativo: cards existentes, inclusive arquivados, "
            "também serão atualizados."
        )
    else:
        print(
            "\nCards de histórias que já estão abertos serão mantidos "
            "sem alterações. Cards arquivados não impedem a criação da nova sprint."
        )


def salvar_relatorio(relatorio, numero_time):
    pasta_relatorios = PASTA_PROJETO / "relatorios"
    pasta_relatorios.mkdir(parents=True, exist_ok=True)
    caminho_relatorio = (
        pasta_relatorios / f"relatorio_trello_time_{numero_time}.json"
    )

    with caminho_relatorio.open("w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, indent=4, ensure_ascii=False)

    return caminho_relatorio


def exibir_relatorio(relatorio, caminho_relatorio):
    print("\nProcessamento do Trello concluído.")
    print(f"Histórias criadas: {len(relatorio['historias_criadas'])}")
    print(f"Histórias atualizadas: {len(relatorio['historias_atualizadas'])}")
    print(f"Histórias ignoradas: {len(relatorio['historias_ignoradas'])}")
    print(f"Tarefas criadas: {len(relatorio['tarefas_criadas'])}")
    print(f"Tarefas atualizadas: {len(relatorio['tarefas_atualizadas'])}")
    print(f"Tarefas ignoradas: {len(relatorio['tarefas_ignoradas'])}")
    print(f"Erros: {len(relatorio['erros'])}")
    print(f"Relatório completo: {caminho_relatorio}")

    if relatorio["avisos"]:
        print("\nCards mantidos sem alterações:")
        for aviso in relatorio["avisos"]:
            print(f"- {aviso}")

    if relatorio["erros"]:
        print("\nErros encontrados:")
        for erro in relatorio["erros"]:
            print(f"- {erro}")


def executar():
    load_dotenv(PASTA_PROJETO / ".env")

    url_original = input("Informe o link da planilha: ").strip()
    numero_time = int(input("Informe o número do time: "))
    link_quadro = input("Informe o link do quadro do Trello: ").strip()
    atualizar = "--atualizar" in sys.argv

    membros_por_time = carregar_membros_por_time()
    id_quadro = pegar_id_quadro(link_quadro)
    membros_quadro = buscar_membros_quadro(id_quadro)
    labels_existentes = buscar_labels_quadro(id_quadro)

    with TemporaryDirectory(prefix="automacao_trello_") as pasta_temporaria:
        url_tsv = xls_to_tsv(url_original)
        caminho_baixado = download_tsv(url_tsv, pasta_temporaria)
        caminho_limpo = limpeza_tsv(caminho_baixado)
        caminho_filtrado = filtrar_por_time(
            caminho_limpo,
            numero_time,
            pasta_temporaria,
        )
        historias = historias_to_dict(caminho_filtrado)
        historias_com_tarefas = extrair_tarefas(historias)
        historias_preparadas = preparar_historias_para_trello(
            historias_com_tarefas,
            numero_time,
            membros_quadro,
            labels_existentes,
            membros_por_time,
        )

        exibir_previa(historias_preparadas, atualizar)
        confirmacao = input("\nDeseja aplicar essas alterações no Trello? [s/N]: ")

        if normalizar_texto(confirmacao) not in {"s", "sim"}:
            print("Operação cancelada. Nenhuma alteração foi feita no Trello.")
            return

        relatorio = montar_quadro_trello(
            id_quadro,
            historias_preparadas,
            atualizar=atualizar,
        )

    caminho_relatorio = salvar_relatorio(relatorio, numero_time)
    exibir_relatorio(relatorio, caminho_relatorio)
    print("Os arquivos TSV temporários foram removidos automaticamente.")


def executar_cli():
    try:
        executar()
    except requests.RequestException as erro:
        print(f"Erro de comunicação: {resumir_erro_trello(erro)}")
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"Erro: {erro}")
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
