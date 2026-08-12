import base64
import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from scripts import supabase_keepalive


def legacy_jwt(role):
    def encode(value):
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return ".".join((encode(dict(alg="HS256", typ="JWT")), encode(dict(role=role)), "signature"))


class SupabaseKeepaliveTests(unittest.TestCase):
    def successful_response(self, rows=None):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = rows if rows is not None else [{"id": 1, "status": "ok"}]
        return response

    def run_keepalive(self, env, response=None):
        stdout = io.StringIO()
        response = response or self.successful_response()
        with patch.dict(
            os.environ,
            {"SUPABASE_URL": "https://example.supabase.co", **env},
            clear=True,
        ), patch.object(
            supabase_keepalive.requests, "get", return_value=response
        ) as get, redirect_stdout(stdout):
            supabase_keepalive.keepalive()
        return get, stdout.getvalue()

    def test_publishable_key_uses_keepalive_get_with_no_bearer_header(self):
        get, output = self.run_keepalive(
            {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_low_privilege"}
        )
        get.assert_called_once_with(
            "https://example.supabase.co/rest/v1/keepalive",
            params={"select": "id,status", "id": "eq.1", "limit": "1"},
            headers={"apikey": "sb_publishable_low_privilege"},
            timeout=10,
        )
        self.assertIn("Using low-privilege Supabase key: publishable", output)
        self.assertIn("Supabase keepalive succeeded", output)

    def test_legacy_anon_key_uses_bearer_header(self):
        anon_key = legacy_jwt("anon")
        get, output = self.run_keepalive({"SUPABASE_ANON_KEY": anon_key})
        self.assertEqual(
            get.call_args.kwargs["headers"],
            {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
        )
        self.assertIn("Using low-privilege Supabase key: legacy anon", output)

    def test_publishable_key_takes_priority_over_other_low_privilege_keys(self):
        get, _ = self.run_keepalive(
            {
                "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_preferred",
                "SUPABASE_ANON_KEY": legacy_jwt("anon"),
                "SUPABASE_KEY": legacy_jwt("anon"),
            }
        )
        self.assertEqual(
            get.call_args.kwargs["headers"], {"apikey": "sb_publishable_preferred"}
        )

    def test_legacy_service_role_jwt_is_rejected_before_request(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": legacy_jwt("service_role"),
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "service_role"):
                supabase_keepalive.keepalive()
        get.assert_not_called()

    def test_secret_key_is_rejected_before_request(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": "sb_secret_high_privilege",
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "secret"):
                supabase_keepalive.keepalive()
        get.assert_not_called()

    def test_unknown_key_type_is_rejected_before_request(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "unrecognized-key",
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "low-privilege"):
                supabase_keepalive.keepalive()
        get.assert_not_called()

    def test_service_role_environment_variable_is_never_read(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": legacy_jwt("service_role"),
            },
            clear=True,
        ), patch.object(supabase_keepalive.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "low-privilege"):
                supabase_keepalive.keepalive()
        get.assert_not_called()

    def test_missing_low_privilege_key_fails(self):
        with patch.dict(
            os.environ, {"SUPABASE_URL": "https://example.supabase.co"}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "low-privilege"):
                supabase_keepalive.keepalive()

    def test_id_one_response_succeeds(self):
        _, output = self.run_keepalive(
            {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_valid"},
            self.successful_response([{"id": 1, "status": "ok"}]),
        )
        self.assertIn("Supabase keepalive succeeded", output)

    def test_empty_response_fails(self):
        with self.assertRaisesRegex(RuntimeError, "id=1"):
            self.run_keepalive(
                {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_valid"},
                self.successful_response([]),
            )

    def test_wrong_id_response_fails(self):
        with self.assertRaisesRegex(RuntimeError, "id=1"):
            self.run_keepalive(
                {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_valid"},
                self.successful_response([{"id": 2, "status": "ok"}]),
            )

    def test_http_error_is_reraised(self):
        response = self.successful_response()
        response.raise_for_status.side_effect = supabase_keepalive.requests.HTTPError(
            "403 Client Error"
        )
        with self.assertRaises(supabase_keepalive.requests.HTTPError):
            self.run_keepalive(
                {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_valid"}, response
            )

    def test_failure_log_does_not_expose_key(self):
        key = "sb_publishable_do_not_log"
        response = self.successful_response()
        response.raise_for_status.side_effect = supabase_keepalive.requests.HTTPError(
            "403 Client Error"
        )
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": key,
            },
            clear=True,
        ), patch.object(
            supabase_keepalive.requests, "get", return_value=response
        ), redirect_stdout(io.StringIO()) as stdout, redirect_stderr(
            io.StringIO()
        ) as stderr:
            with self.assertRaises(supabase_keepalive.requests.HTTPError):
                supabase_keepalive.main()
        logs = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(key, logs)
        self.assertIn("Supabase keepalive failed: 403 Client Error", logs)

    def test_missing_url_fails_clearly(self):
        with patch.dict(
            os.environ,
            {"SUPABASE_PUBLISHABLE_KEY": "sb_publishable_valid"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_URL"):
                supabase_keepalive.keepalive()


if __name__ == "__main__":
    unittest.main()
