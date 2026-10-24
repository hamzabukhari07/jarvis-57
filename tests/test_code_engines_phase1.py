import unittest
from core.code_engines import (
    ENGINES,
    resolve_binary,
    probe_engine,
    probe_all_engines,
    get_default_engine,
    set_default_engine,
)
from actions.code_engines_status import handler, TOOL


class TestCodeEnginesPhase1(unittest.TestCase):
    def test_engine_registry_contains_expected_engines(self):
        self.assertIn("antigravity", ENGINES)
        self.assertIn("opencode", ENGINES)
        self.assertIn("kilo", ENGINES)

        for eid, engine in ENGINES.items():
            self.assertEqual(engine.id, eid)
            self.assertTrue(len(engine.label) > 0)
            self.assertTrue(len(engine.path_names) > 0)
            self.assertTrue(len(engine.vendor_dirs) > 0)
            self.assertTrue(len(engine.backs_tool) > 0)

    def test_resolve_binary_known_and_unknown(self):
        # Unknown engine should return None
        self.assertIsNone(resolve_binary("non_existent_engine_id"))

        # Registered engines should return str or None without throwing
        for eid in ("antigravity", "opencode", "kilo"):
            bin_path = resolve_binary(eid)
            if bin_path is not None:
                self.assertIsInstance(bin_path, str)

    def test_probe_engine_schema_and_states(self):
        valid_states = {"ready", "sign_in_required", "not_installed", "off", "unknown"}

        for eid in ENGINES:
            res = probe_engine(eid)
            self.assertEqual(res["id"], eid)
            self.assertIn(res["state"], valid_states)
            self.assertIn("backs_tool", res)
            self.assertIn("timestamp", res)
            self.assertIn("reason", res)
            self.assertIsInstance(res["models"], list)

        # Unknown engine probe
        unk = probe_engine("unknown_engine_99")
        self.assertEqual(unk["state"], "unknown")

    def test_probe_all_engines(self):
        all_res = probe_all_engines()
        self.assertEqual(len(all_res), 3)
        ids = [e["id"] for e in all_res]
        self.assertListEqual(sorted(ids), ["antigravity", "kilo", "opencode"])

    def test_default_engine_read_and_set(self):
        initial = get_default_engine()
        self.assertIn(initial, ENGINES)

        ok = set_default_engine("opencode")
        self.assertTrue(ok)
        self.assertEqual(get_default_engine(), "opencode")

        # Restore
        set_default_engine(initial)

    def test_action_tool_declaration_and_handler(self):
        self.assertEqual(TOOL["name"], "code_engines_status")
        self.assertIn("handler", TOOL)
        self.assertTrue(callable(TOOL["handler"]))

        # Action: list
        list_res = handler({"action": "list"})
        self.assertEqual(list_res["status"], "success")
        self.assertEqual(list_res["action"], "list")
        self.assertIn("engines", list_res)
        self.assertIn("summary", list_res)
        self.assertIn("ready_engines", list_res)

        # Action: check
        check_res = handler({"action": "check", "engine": "antigravity"})
        self.assertEqual(check_res["status"], "success")
        self.assertEqual(check_res["action"], "check")
        self.assertIn("engine", check_res)
        self.assertIn("summary", check_res)

        # Action: invalid engine
        bad_res = handler({"action": "check", "engine": "invalid_engine"})
        self.assertEqual(bad_res["status"], "error")


if __name__ == "__main__":
    unittest.main()
