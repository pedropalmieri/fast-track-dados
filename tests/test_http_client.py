"""Simulo falhas de rede para testar retentativas sem depender das APIs."""

import unittest
from unittest.mock import Mock, patch

import requests

from src.http_client import ApiError, HttpClient


def response(status: int, payload: dict | None = None, retry_after: str = "") -> Mock:
    result = Mock(status_code=status, ok=status < 400)
    result.headers = {"Retry-After": retry_after}
    result.json.return_value = payload or {"ok": True}
    return result


class HttpClientTests(unittest.TestCase):
    @patch("src.http_client.time.sleep")
    def test_retries_429_and_respects_retry_after(self, sleep: Mock) -> None:
        client = HttpClient(interval=0)
        client.session.get = Mock(side_effect=[response(429, retry_after="7"), response(200)])
        self.assertEqual(client.get("https://example.test"), {"ok": True})
        self.assertEqual(client.session.get.call_count, 2)
        sleep.assert_any_call(7.0)

    @patch("src.http_client.time.sleep")
    def test_timeout_and_server_error_have_limited_retries(self, sleep: Mock) -> None:
        client = HttpClient(interval=0, attempts=3)
        client.session.get = Mock(side_effect=[requests.Timeout(), response(503), response(503)])
        with self.assertRaises(ApiError):
            client.get("https://example.test")
        self.assertEqual(client.session.get.call_count, 3)

    @patch("src.http_client.time.sleep")
    def test_authentication_error_is_not_retried_or_exposed(self, sleep: Mock) -> None:
        client = HttpClient(interval=0)
        client.session.get = Mock(return_value=response(401))
        with self.assertRaises(ApiError) as error:
            client.get("https://example.test", {"api_key": "segredo-de-teste"})
        self.assertNotIn("segredo-de-teste", str(error.exception))
        self.assertEqual(client.session.get.call_count, 1)

    @patch("src.http_client.time.sleep")
    def test_interval_between_calls(self, sleep: Mock) -> None:
        client = HttpClient(interval=2)
        client.session.get = Mock(return_value=response(200))
        with patch("src.http_client.time.monotonic", return_value=10.0):
            client.get("https://example.test")
            client.get("https://example.test")
        sleep.assert_any_call(2.0)

    @patch("src.http_client.time.sleep")
    def test_invalid_json_fails_without_returning_html(self, sleep: Mock) -> None:
        client = HttpClient(interval=0)
        invalid = response(200)
        invalid.json.side_effect = ValueError("conteúdo externo")
        client.session.get = Mock(return_value=invalid)
        with self.assertRaises(ApiError):
            client.get("https://example.test")


if __name__ == "__main__":
    unittest.main()
