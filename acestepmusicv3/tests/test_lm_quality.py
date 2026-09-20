import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "files" / "lm_quality.py"
SPEC = importlib.util.spec_from_file_location("lm_quality", MODULE_PATH)
quality = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(quality)


def codes(values):
    return "".join(f"<|audio_code_{value}|>" for value in values)


class AudioCodeQualityTest(unittest.TestCase):
    def test_accepts_full_diverse_plan(self):
        result = {"success": True, "audio_codes": codes(index % 211 for index in range(900))}
        self.assertTrue(quality.assess_audio_codes(result, 180).accepted)

    def test_rejects_truncated_and_collapsed_plans(self):
        truncated = {"success": True, "audio_codes": codes(range(40))}
        collapsed = {"success": True, "audio_codes": codes([7] * 900)}
        self.assertFalse(quality.assess_audio_codes(truncated, 180).accepted)
        self.assertFalse(quality.assess_audio_codes(collapsed, 180).accepted)

    def test_retry_seeds_are_stable_and_distinct(self):
        self.assertEqual(quality.retry_seeds([42, 43], 1), [1000045, 1000046])
        self.assertEqual(quality.retry_seeds([42], 2), [2000048])


if __name__ == "__main__":
    unittest.main()
