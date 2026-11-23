import json
import unittest
from unittest.mock import patch

from src.consultar_views import consultar


class ConsultaTests(unittest.TestCase):
    @patch("src.consultar_views._cli")
    def test_annual_com_filtro(self, cli):
        cli.side_effect = [[{"id": "wh"}], {
            "status": {"state": "SUCCEEDED"},
            "manifest": {"schema": {"columns": [{"name": "year"}]}},
            "result": {"data_array": [["2025"]]},
        }]
        self.assertEqual(consultar("annual", ano=2025, limite=1), [{"year": "2025"}])
        payload = json.loads(cli.call_args.args[-1])
        self.assertEqual(payload["warehouse_id"], "wh")
        self.assertIn("workspace.fast_track_dados.annual WHERE year = :ano", payload["statement"])
        self.assertEqual(payload["parameters"][0]["value"], "2025")
        self.assertTrue(payload["statement"].endswith("LIMIT 1"))

    @patch("src.consultar_views._cli")
    def test_rejeita_entradas_antes_de_conectar(self, cli):
        for view, limite in [("outra", 10), ("production", 101), ("topics", 0)]:
            with self.assertRaises(ValueError):
                consultar(view, limite=limite)
        cli.assert_not_called()

    @patch("src.consultar_views._cli", return_value=[{"id": "a"}, {"id": "b"}])
    def test_warehouse_ambiguo(self, cli):
        with self.assertRaisesRegex(ValueError, "DATABRICKS_WAREHOUSE_ID"):
            consultar("annual")

    @patch("src.consultar_views._cli", return_value={"status": {"state": "CANCELED"}})
    def test_cancelamento_nao_retorna_lista_vazia(self, cli):
        with self.assertRaisesRegex(RuntimeError, "CANCELED"):
            consultar("annual", warehouse_id="wh")
