import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "files" / "lyrics_alignment.py"
SPEC = importlib.util.spec_from_file_location("lyrics_alignment", MODULE_PATH)
alignment = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(alignment)


class LyricsAlignmentTest(unittest.TestCase):
    def test_chinese_and_english_sentences_skip_section_tags(self):
        result = alignment.alignment_segments(
            "[00:00.50][Verse 1]\n[00:01.20]雨落在窗前\n[00:04.50]Coming home",
            8.0,
        )
        self.assertEqual([item["text"] for item in result["segments"]], ["雨落在窗前", "Coming home"])
        self.assertEqual(result["segments"][0]["end_seconds"], 4.5)
        self.assertEqual(result["segments"][1]["end_seconds"], 8.0)

    def test_out_of_bounds_and_non_monotonic_timestamps_are_rejected(self):
        for lrc in (
            "[00:11.00]too late",
            "[00:02.00]one\n[00:01.00]two",
            "[00:00.00][Instrumental]",
        ):
            with self.subTest(lrc=lrc), self.assertRaises(ValueError):
                alignment.alignment_segments(lrc, 10.0)

    def test_equal_native_timestamps_are_split_without_losing_sentences(self):
        result = alignment.alignment_segments(
            "[00:01.00]First line\n[00:01.00]Second line\n[00:05.00]Final line",
            9.0,
        )
        self.assertEqual(
            result["segments"],
            [
                {"text": "First line", "start_seconds": 1.0, "end_seconds": 3.0},
                {"text": "Second line", "start_seconds": 3.0, "end_seconds": 5.0},
                {"text": "Final line", "start_seconds": 5.0, "end_seconds": 9.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
