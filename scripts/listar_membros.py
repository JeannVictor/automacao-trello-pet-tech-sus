from dotenv import load_dotenv

from automacao_trello.configuracao import PASTA_PROJETO
from automacao_trello.trello_api import (
    buscar_membros_quadro,
    pegar_id_quadro,
)


def main():
    load_dotenv(PASTA_PROJETO / ".env")
    link_quadro = input("Informe o link do quadro do Trello: ").strip()
    id_quadro = pegar_id_quadro(link_quadro)
    membros = buscar_membros_quadro(id_quadro)

    print("\nMembros encontrados:")

    for membro in membros:
        print(
            f"- {membro['fullName']} "
            f"(@{membro['username']}) -> {membro['id']}"
        )


if __name__ == "__main__":
    main()
