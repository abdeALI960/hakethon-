import base64
import unittest

from backend.services.redaction import redact_logs


class RedactionTests(unittest.TestCase):
    def test_redacts_credentials_and_personal_data(self) -> None:
        base64_secret = base64.b64encode(b"this-is-a-long-secret-value-for-redaction").decode()
        lines = [
            "Authorization: Bearer abc.def-123",
            "api_key=sk-" + "a" * 24,
            "google_key=AIza" + "b" * 30,
            "password=hunter2",
            '{"client_secret":"hidden-secret"}',
            "contact operator@example.com",
            "jwt=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "hex=" + "a" * 40,
            "base64=" + base64_secret,
        ]

        redacted = redact_logs(lines)
        joined = "\n".join(redacted)
        for secret in (
            "abc.def-123",
            "sk-" + "a" * 24,
            "AIza" + "b" * 30,
            "hunter2",
            "hidden-secret",
            "operator@example.com",
            "eyJhbGciOiJIUzI1NiJ9",
            "a" * 40,
            base64_secret,
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, joined)

    def test_caps_line_count_and_character_count(self) -> None:
        redacted = redact_logs(["x" * 600 for _ in range(205)])
        self.assertEqual(len(redacted), 200)
        self.assertTrue(all(len(line) <= 500 for line in redacted))

    def test_redacts_generator_without_consuming_beyond_limit(self) -> None:
        consumed: list[int] = []

        def logs():
            for index in range(5):
                consumed.append(index)
                yield f"line-{index}"

        self.assertEqual(redact_logs(logs(), max_lines=2), ["line-0", "line-1"])
        self.assertEqual(consumed, [0, 1])


if __name__ == "__main__":
    unittest.main()
