import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from api_client import APISettings, ModelAPIError, load_config, stream_chat
from rag_pipeline import FinlandTravelRAG


class MockModelServer(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, self.headers.get("Authorization"), payload))
        self.send_response(self.server.status)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.server.status != 200:
            self.wfile.write(b"sensitive-provider-error-unit-test-key")
        else:
            self.wfile.write(self.server.body.encode("utf-8"))


def event(value):
    return "data: " + json.dumps(value, ensure_ascii=False) + "\n\n"


class APITests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), MockModelServer)
        self.server.requests = []
        self.server.status = 200
        self.server.body = (
            ": heartbeat\n\n"
            + event({"choices": [{"delta": {"reasoning_content": "private reasoning"}}]})
            + event({"choices": [{"delta": {"content": "最佳时间为9月"}}]})
            + event({"choices": [{"delta": {"content": "至次年3月。"}}]})
            + event({"choices": [{"delta": {}, "finish_reason": "stop"}]})
            + event({"choices": [], "usage": {"total_tokens": 10}})
            + "data: [DONE]\n\n"
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.settings = APISettings(api_key="unit-test-key", provider="custom", model="test-model",
                                    base_url=f"http://127.0.0.1:{self.server.server_port}/v1")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_rag_streams_chinese_with_real_http_and_sources(self):
        rag = FinlandTravelRAG(mode="api", api_settings=self.settings)
        with patch.object(rag, "_ensure_models", side_effect=AssertionError("API mode must not load local models")):
            answer = rag.generate_response("芬兰什么时候看极光？")
        self.assertIn("最佳时间为9月至次年3月。", answer)
        self.assertIn("northern_lights_guide.pdf", answer)
        self.assertNotIn("private reasoning", answer)
        path, auth, payload = self.server.requests[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(auth, "Bearer unit-test-key")
        self.assertEqual(payload["model"], "test-model")
        self.assertTrue(payload["stream"])
        self.assertIn("September to March", payload["messages"][1]["content"])
        self.assertNotIn("unit-test-key", json.dumps(payload))
        self.assertEqual(payload["max_tokens"], 512)

    def test_no_relevant_documents_means_no_paid_api_call(self):
        rag = FinlandTravelRAG(mode="api", api_settings=self.settings)
        self.assertIn("No relevant content found", rag.generate_response("quantum superconductivity"))
        self.assertEqual(self.server.requests, [])

    def test_status_errors_are_safe_and_do_not_retry(self):
        for status in (302, 401, 403, 404, 429, 500):
            with self.subTest(status=status):
                self.server.status = status
                before = len(self.server.requests)
                with self.assertRaises(ModelAPIError) as caught:
                    list(stream_chat(self.settings, "aurora", "some context"))
                self.assertNotIn("unit-test-key", str(caught.exception))
                self.assertNotIn("sensitive-provider-error", str(caught.exception))
                self.assertEqual(len(self.server.requests), before + 1)

    def test_malformed_empty_and_interrupted_streams(self):
        for body in ("data: invalid-json\n\n", "data: [DONE]\n\n",
                     event({"choices": [{"delta": {"content": "partial"}}]}),
                     event({"error": {"message": "unit-test-key"}})):
            with self.subTest(body=body):
                self.server.body = body
                with self.assertRaises(ModelAPIError) as caught:
                    list(stream_chat(self.settings, "aurora", "context"))
                self.assertNotIn("unit-test-key", str(caught.exception))

    def test_api_chat_interface(self):
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"APP_MODE": "api", "APP_ACCESS_PASSWORD": "", "LLM_PROVIDER": "custom",
                                    "LLM_BASE_URL": self.settings.base_url, "LLM_MODEL": "test-model",
                                    "LLM_API_KEY": "unit-test-key"}):
            app = AppTest.from_file(str(BASE_DIR / "app.py"))
            # A nonempty test secret prevents AppTest from reading real deployment credentials.
            app.secrets = {"TEST_MODE": True}
            app.run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.selectbox[0].value, "Online AI answers")
            app.chat_input[0].set_value("芬兰什么时候看极光？").run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 0)
            self.assertEqual(len(app.chat_message), 2)
            self.assertIn("最佳时间为9月至次年3月。", app.chat_message[1].markdown[0].value)


class ConfigurationTests(unittest.TestCase):
    def test_missing_key_disables_only_api_chat(self):
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"APP_MODE": "api", "APP_ACCESS_PASSWORD": "", "LLM_API_KEY": "",
                                    "DASHSCOPE_API_KEY": "", "LLM_PROVIDER": "qwen",
                                    "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1"}):
            app = AppTest.from_file(str(BASE_DIR / "app.py"))
            app.secrets = {"TEST_MODE": True}
            app.run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.chat_input[0].disabled)
            self.assertTrue(any("not enabled yet" in warning.value for warning in app.warning))
            app.selectbox[0].select("Document search").run(timeout=20)
            self.assertFalse(app.chat_input[0].disabled)

    def test_provider_defaults_and_safe_repr(self):
        qwen = APISettings.from_mapping({"DASHSCOPE_API_KEY": "test-qwen-key"})
        self.assertTrue(qwen.configured)
        self.assertNotIn("test-qwen-key", repr(qwen))
        deepseek = APISettings.from_mapping({"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "test-deepseek-key"})
        self.assertEqual(deepseek.base_url, "https://api.deepseek.com")
        self.assertFalse(APISettings.from_mapping({}).configured)

    def test_configuration_priority_and_no_environment_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / ".env").write_text("LLM_MODEL=local-model\nLLM_API_KEY=local-key\n", encoding="utf-8")
            with patch.dict(os.environ, {"LLM_MODEL": "environment-model"}):
                before = dict(os.environ)
                values = load_config(Path(folder), {"LLM_MODEL": "secret-model", "LLM_API_KEY": "secret-key"})
                self.assertEqual(values["LLM_MODEL"], "environment-model")
                self.assertEqual(values["LLM_API_KEY"], os.environ.get("LLM_API_KEY", "secret-key"))
                self.assertEqual(dict(os.environ), before)

    def test_rejects_unsafe_or_invalid_configuration(self):
        for values in ({"LLM_BASE_URL": "http://public.example/v1"},
                       {"LLM_BASE_URL": "https://user:password@example.com/v1"},
                       {"LLM_BASE_URL": "https://example.com/v1?key=secret"},
                       {"LLM_PROVIDER": "custom"}, {"LLM_PROVIDER": "unsupported"},
                       {"LLM_MAX_TOKENS": "unlimited"}, {"LLM_MAX_TOKENS": "999999"}):
            with self.subTest(values=values):
                with self.assertRaises(ModelAPIError):
                    APISettings.from_mapping(values)
        with self.assertRaisesRegex(ModelAPIError, "API key"):
            list(stream_chat(APISettings(), "question", "context"))

    def test_optional_access_password(self):
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"APP_ACCESS_PASSWORD": "test-only-password", "APP_MODE": "offline"}):
            app = AppTest.from_file(str(BASE_DIR / "app.py"))
            app.secrets = {"TEST_MODE": True}
            app.run(timeout=20)
            self.assertEqual(len(app.chat_input), 0)
            app.text_input[0].set_value("wrong")
            app.button[0].click().run(timeout=20)
            self.assertIn("Incorrect access password", app.error[0].value)
            app.text_input[0].set_value("test-only-password")
            app.button[0].click().run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.chat_input), 1)


if __name__ == "__main__":
    unittest.main()
