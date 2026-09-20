import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "files" / "lyrics_readability.py"
SPEC = importlib.util.spec_from_file_location("lyrics_readability", MODULE_PATH)
readability = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(readability)


PHONETIC = """[Verse 1]
[zh] ye4 se4 luo4 zai4 jian1 shang4
[zh] lu4 deng1 ba3 ying3 zi5 la1 chang2

[Chorus]
[zh] zai4 zou3 yi1 duan4
[zh] jiu4 dao4 jia1 le5"""

READABLE = """[Verse 1]
夜色落在肩上
路灯把影子拉长

[Chorus]
再走一段
就到家了再见故乡"""


class LyricsReadabilityTest(unittest.TestCase):
    def test_classifies_official_phonetics_without_converting_them(self):
        self.assertEqual(readability.phonetic_kind(PHONETIC, "zh"), "phonetic")
        self.assertEqual(readability.phonetic_kind(READABLE, "zh"), "han")
        self.assertEqual(readability.phonetic_kind("[Verse]\nloram ipsum dolor sit amet", "zh"), "invalid")

    def test_rejects_latin_gibberish_but_allows_a_small_english_hook(self):
        mixed = READABLE.replace("再走一段", "théwēi yīfān lìch gōng")
        self.assertEqual(readability.phonetic_kind(mixed, "zh"), "invalid")
        hook = READABLE.replace("再走一段", "yeah oh")
        self.assertEqual(readability.phonetic_kind(hook, "zh"), "han")

    def test_non_chinese_language_is_not_subject_to_chinese_classifier(self):
        self.assertEqual(readability.phonetic_kind("ordinary English lyrics", "en"), "han")


if __name__ == "__main__":
    unittest.main()
