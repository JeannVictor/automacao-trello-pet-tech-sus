import unittest

from automacao_trello.membros import buscar_ids_responsaveis
from automacao_trello.preparacao import (
    definir_cores_historia,
    reservar_labels_tus,
)
from automacao_trello.tarefas import extrair_tarefas


class TestRegras(unittest.TestCase):
    def test_cores_do_gat_4(self):
        historia = {
            "Time/Responsável": "GAT-4",
            "Título": "História coletiva",
            "Observação": "Atividade Recorrente",
        }

        self.assertEqual(
            definir_cores_historia(historia, 1),
            {"us": "green_light", "tus": "green_dark"},
        )

    def test_cores_da_reuniao_recorrente(self):
        historia = {
            "Time/Responsável": "TIME 1 - Projeto (Pessoa)",
            "Título": "Orientar a equipe no projeto",
            "Observação": "Atividade Recorrente",
        }

        self.assertEqual(
            definir_cores_historia(historia, 1),
            {"us": "red", "tus": "red_dark"},
        )

    def test_cores_do_burndown_diario(self):
        historia = {
            "ID": "US-1401",
            "Time/Responsável": "TIME 1 - Projeto (Pessoa)",
            "Título": "Atualizar diariamente o gráfico Sprint Burndown",
            "Observação": "Atividade Recorrente",
        }

        self.assertEqual(
            definir_cores_historia(historia, 1),
            {"us": "red", "tus": "red_dark"},
        )

    def test_reaproveita_bloco_de_labels_tus(self):
        labels = [
            {"id": "a", "name": "TUS-4000", "uses": 0},
            {"id": "b", "name": "TUS-4001", "uses": 0},
        ]

        resultado = reservar_labels_tus(labels, 2, set())

        self.assertEqual(
            [label["name"] for label in resultado],
            ["TUS-4000", "TUS-4001"],
        )

    def test_gat_4_recebe_todos_os_membros_do_quadro(self):
        membros_quadro = [{"id": "membro-1"}, {"id": "membro-2"}]

        ids, pendencias = buscar_ids_responsaveis(
            "GAT-4",
            1,
            membros_quadro,
            {"1": []},
        )

        self.assertEqual(ids, ["membro-1", "membro-2"])
        self.assertEqual(pendencias, [])

    def test_extrai_tarefas(self):
        historias = [
            {
                "Critério de Aceitação": (
                    "Critérios gerais  🛠 Possíveis Tarefas "
                    "- Implementar recurso - Revisar resultado"
                )
            }
        ]

        resultado = extrair_tarefas(historias)

        self.assertEqual(
            resultado[0]["Tarefas"],
            ["Implementar recurso", "Revisar resultado"],
        )


if __name__ == "__main__":
    unittest.main()
