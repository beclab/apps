import json
import os
import unittest
import urllib.error
import urllib.request


class FlareSolverrApiTest(unittest.TestCase):
    """Live /v1 functional checks. Set FLARESOLVERR_URL to the solver base."""

    @classmethod
    def setUpClass(cls):
        cls.base = (os.environ.get("FLARESOLVERR_URL") or "").rstrip("/")
        if not cls.base:
            raise unittest.SkipTest(
                "set FLARESOLVERR_URL to run FlareSolverr API functional tests"
            )

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw)

    def _post(self, payload):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base + "/v1",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def test_root_reports_ready_version(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertEqual(body["version"], "3.5.0")
        self.assertIn("ready", body["msg"].lower())
        self.assertTrue(body.get("userAgent"))

    def test_health_ok(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "ok")

    def test_sessions_create_list_and_destroy(self):
        http, listed = self._post({"cmd": "sessions.list"})
        self.assertEqual(http, 200)
        self.assertEqual(listed["status"], "ok")
        self.assertEqual(listed["version"], "3.5.0")
        self.assertIsInstance(listed.get("sessions"), list)

        http, created = self._post({"cmd": "sessions.create"})
        self.assertEqual(http, 200)
        self.assertEqual(created["status"], "ok")
        session = created["session"]
        self.assertTrue(session)

        http, listed = self._post({"cmd": "sessions.list"})
        self.assertIn(session, listed["sessions"])

        http, destroyed = self._post(
            {"cmd": "sessions.destroy", "session": session}
        )
        self.assertEqual(http, 200)
        self.assertEqual(destroyed["status"], "ok")

    def test_request_get_example_com(self):
        http, created = self._post({"cmd": "sessions.create"})
        session = created["session"]
        try:
            http, body = self._post(
                {
                    "cmd": "request.get",
                    "url": "https://example.com",
                    "maxTimeout": 60000,
                    "session": session,
                }
            )
            self.assertEqual(http, 200)
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["version"], "3.5.0")
            solution = body["solution"]
            self.assertEqual(solution["status"], 200)
            self.assertIn("example.com", solution["url"])
            self.assertIn("Example Domain", solution["response"])
        finally:
            self._post({"cmd": "sessions.destroy", "session": session})

    def test_invalid_cmd_returns_error(self):
        http, body = self._post({"cmd": "not-a-command"})
        self.assertEqual(body["status"], "error")
        self.assertIn("cmd", body["message"])
        self.assertEqual(body["version"], "3.5.0")
        self.assertIn(http, (200, 500))


if __name__ == "__main__":
    unittest.main()
