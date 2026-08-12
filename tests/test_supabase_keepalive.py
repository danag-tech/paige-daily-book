import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from scripts import supabase_keepalive


class SupabaseKeepaliveTests(unittest.TestCase):
    def test_keepalive_performs_one_read_only_limited_query(self):
        response = Mock()
        response.raise_for_status.return_value = None

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co/",
                "SUPABASE_SERVICE_ROLE_KEY": "service-secret",
                "SUPABASE_KEY": "legacy-secret",
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get", return_value=response) as get, redirect_stdout(
            io.StringIO()
        ) as stdout:
            supabase_keepalive.keepalive()

        get.assert_called_once_with(
            "https://example.supabase.co/rest/v1/subscribers",
            params={"select": "email", "limit": "1"},
            headers={
                "apikey": "service-secret",
                "Authorization": "Bearer service-secret",
            },
            timeout=10,
        )
        self.assertEqual(stdout.getvalue().strip(), "Supabase keepalive succeeded")

    def test_keepalive_falls_back_to_existing_supabase_key(self):
        response = Mock()
        response.raise_for_status.return_value = None

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "legacy-secret",
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get", return_value=response) as get:
            supabase_keepalive.keepalive()

        self.assertEqual(get.call_args.kwargs["headers"]["apikey"], "legacy-secret")

    def test_main_reports_request_failure_without_exposing_key_and_reraises(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "do-not-log-this-key",
            },
            clear=True,
        ), patch.object(
            supabase_keepalive.requests,
            "get",
            side_effect=supabase_keepalive.requests.RequestException("connection failed"),
        ), redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(supabase_keepalive.requests.RequestException):
                supabase_keepalive.main()

        error_output = stderr.getvalue()
        self.assertIn("Supabase keepalive failed: connection failed", error_output)
        self.assertNotIn("do-not-log-this-key", error_output)

    def test_missing_configuration_fails_clearly(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_URL"):
                supabase_keepalive.keepalive()


if __name__ == "__main__":
    unittest.main()
