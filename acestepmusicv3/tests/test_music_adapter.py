import importlib.util
import base64
import io
import pathlib
import sys
import tempfile
import time
import urllib.parse
import unittest
from email.message import Message
from unittest import mock

from fastapi.testclient import TestClient


MODULE_PATH = pathlib.Path(__file__).parents[1] / "files" / "music_adapter.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("music_adapter", MODULE_PATH)
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)


class AudioResponse(io.BytesIO):
    def __init__(self, body: bytes):
        super().__init__(body)
        self.headers = Message()
        self.headers["Content-Type"] = "audio/wav"


class MusicAdapterContractTest(unittest.TestCase):
    def setUp(self):
        adapter.TASKS.clear()
        self.client = TestClient(adapter.app)
        self.temp_directory = tempfile.TemporaryDirectory()
        self.temp_dir = pathlib.Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_create_poll_content_and_contract_errors(self):
        def native(path, _payload=None):
            if path == "/release_task":
                return {"code": 200, "data": {"task_id": "task-1"}}
            if path == "/query_result":
                return {
                    "code": 200,
                    "data": [{
                        "task_id": "task-1",
                        "status": 1,
                        "result": '[{"file":"/v1/audio?path=%2Ftmp%2Fsong.wav","metas":{"duration":240}}]',
                    }],
                }
            raise AssertionError(path)

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post(
                "/v1/music/generations",
                json={"model": "ace", "prompt": "Mandarin indie pop", "lyrics": "[Verse 1]\n雨", "duration_seconds": 240},
            )
            self.assertEqual(created.status_code, 202)
            self.assertEqual(created.json()["status"], "queued")

            completed = self.client.get("/v1/music/generations/task-1")
            self.assertEqual(completed.status_code, 200)
            body = completed.json()
            self.assertEqual(body["status"], "completed")
            self.assertEqual(body["outputs"][0]["duration_seconds"], 240)
            output_id = body["outputs"][0]["id"]

        with mock.patch.object(adapter.urllib.request, "urlopen", return_value=AudioResponse(b"RIFFmusic")):
            content = self.client.get(f"/v1/music/generations/task-1/content?output_id={output_id}")
            self.assertEqual(content.status_code, 200)
            self.assertEqual(content.headers["content-type"], "audio/wav")
            self.assertEqual(content.content, b"RIFFmusic")

        cancel = self.client.delete("/v1/music/generations/task-1")
        self.assertEqual(cancel.status_code, 422)
        self.assertEqual(cancel.json()["error"]["code"], "cancellation_unsupported")
        lost = self.client.get("/v1/music/generations/from-old-process")
        self.assertEqual(lost.status_code, 410)
        self.assertEqual(lost.json()["error"]["code"], "task_lost")

    def test_instrumental_rejects_lyrics_and_engine_spec_is_single_worker(self):
        response = self.client.post(
            "/v1/music/generations",
            json={"prompt": "ambient", "lyrics": "words", "instrumental": True},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "lyrics_not_allowed")
        spec = self.client.get("/api/engine-spec").json()
        self.assertEqual(spec["mode"], "music_generation")
        self.assertEqual(spec["max_concurrency"], 1)
        self.assertEqual(
            spec["serves"], ["music.generate", "music.repaint", "music.format", "music.draft", "music.lyrics_alignment"]
        )
        self.assertIn(
            {"method": "GET", "path": "/v1/music/generations/{id}/lyrics-alignment", "available": True},
            spec["endpoints"],
        )
        self.assertEqual(spec["extensions"]["music"]["default_quality_profile"], "high_quality")
        self.assertEqual(spec["extensions"]["music"]["default_production_profile"], "clean")
        self.assertEqual(spec["extensions"]["music"]["default_caption_mode"], "preserve")
        self.assertEqual(spec["extensions"]["music"]["vocal_languages"], list(adapter.VOCAL_LANGUAGES))
        self.assertNotIn("unknown", spec["extensions"]["music"]["vocal_languages"])

    def test_alignment_is_persisted_and_read_after_task_memory_is_cleared(self):
        audio = self.temp_dir / "song.wav"
        audio.write_bytes(b"RIFF")
        sidecar = pathlib.Path(str(audio) + ".lyrics-alignment.json")
        sidecar.write_text(
            '{"segments":[{"text":"[zh] yu3 luo4 zai4 chuang1 qian2","start_seconds":1.2,"end_seconds":4.5}]}',
            encoding="utf-8",
        )
        adapter.TASKS["new-song"] = {
            "display_lyrics": "[Verse 1]\n雨落在窗前",
            "conditioning_lyrics": "[Verse 1]\n[zh] yu3 luo4 zai4 chuang1 qian2",
        }
        with mock.patch.object(adapter, "ALIGNMENT_AUDIO_ROOTS", (str(self.temp_dir),)), mock.patch.object(
            adapter, "LYRICS_ALIGNMENT_DIR", str(self.temp_dir / "persisted")
        ):
            self.assertTrue(
                adapter._persist_alignment(
                    "new-song", "/v1/audio?path=" + urllib.parse.quote(str(audio), safe=""), 10.0
                )
            )
            adapter.TASKS.clear()
            response = self.client.get("/v1/music/generations/new-song/lyrics-alignment")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["segments"][0]["text"], "雨落在窗前")

            old = self.client.get("/v1/music/generations/old-song/lyrics-alignment")
            self.assertEqual(old.status_code, 404)
            self.assertEqual(old.json()["error"]["code"], "lyrics_alignment_unavailable")

    def test_alignment_rejects_out_of_range_and_incomplete_generations(self):
        audio = self.temp_dir / "song.wav"
        audio.write_bytes(b"RIFF")
        pathlib.Path(str(audio) + ".lyrics-alignment.json").write_text(
            '{"segments":[{"text":"too late","start_seconds":9,"end_seconds":12}]}',
            encoding="utf-8",
        )
        with mock.patch.object(adapter, "ALIGNMENT_AUDIO_ROOTS", (str(self.temp_dir),)), mock.patch.object(
            adapter, "LYRICS_ALIGNMENT_DIR", str(self.temp_dir / "persisted")
        ):
            self.assertFalse(
                adapter._persist_alignment(
                    "bad-song", "/v1/audio?path=" + urllib.parse.quote(str(audio), safe=""), 10.0
                )
            )
            adapter.TASKS["queued-song"] = {"id": "queued-song", "status": "running"}
            queued = self.client.get("/v1/music/generations/queued-song/lyrics-alignment")
            self.assertEqual(queued.status_code, 409)
            self.assertEqual(queued.json()["error"]["code"], "lyrics_alignment_unavailable")

    def test_format_input_is_async_and_exposes_draft_and_effective_versions(self):
        calls = []

        def native(path, payload=None, timeout=30):
            self.assertEqual(path, "/format_input")
            self.assertEqual(timeout, 300)
            calls.append(payload)
            return {"code": 200, "data": {"caption": "Polished Mandarin pop", "lyrics": "[Verse 1]\n风来了\n我穿过很长的街\n\n[Chorus]\n回家\n回家"}}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post(
                "/v1/music/formats",
                json={
                    "model": "ace",
                    "prompt": "Mandarin pop",
                    "lyrics": "[Verse 1]\n风吹过街边\n\n[Chorus]\n回家",
                    "vocal_language": "zh",
                    "duration_seconds": 240,
                },
            )
            self.assertEqual(created.status_code, 202)
            task_id = created.json()["id"]
            result = created.json()
            for _ in range(50):
                result = self.client.get(f"/v1/music/formats/{task_id}").json()
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["draft_prompt"], "Mandarin pop")
        self.assertEqual(result["effective_prompt"], "Polished Mandarin pop")
        self.assertIn("我穿过很长的街", result["effective_lyrics"])
        self.assertEqual(result["metrics"]["uniformity_risk"], "low")
        self.assertEqual(calls[0]["param_obj"], '{"duration": 240, "language": "zh"}')

        lost = self.client.get("/v1/music/formats/fmt_from_old_process")
        self.assertEqual(lost.status_code, 410)
        self.assertEqual(lost.json()["error"]["code"], "task_lost")

    def test_dual_lyrics_are_returned_and_condition_only_native_generation(self):
        phonetic = "[Verse 1]\n[zh] ye4 se4 luo4 zai4 jian1 shang4\n[zh] lu4 deng1 ba3 ying3 zi5 la1 chang2"
        readable = "[Verse 1]\n夜色落在肩上照亮回家的方向\n路灯把影子拉长陪我穿过街巷"
        payloads = []

        def native(path, payload=None, timeout=30):
            payloads.append(payload)
            if path == "/format_input":
                return {"code": 200, "data": {"caption": "Mandarin pop", "lyrics": readable, "conditioning_lyrics": phonetic}}
            if path == "/release_task":
                return {"code": 200, "data": {"task_id": "dual-song"}}
            raise AssertionError(path)

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post("/v1/music/formats", json={
                "model": "ace", "prompt": "Mandarin pop", "lyrics": readable,
                "vocal_language": "zh", "duration_seconds": 180,
            })
            task_id = created.json()["id"]
            for _ in range(50):
                formatted = self.client.get(f"/v1/music/formats/{task_id}").json()
                if formatted["status"] == "completed":
                    break
                time.sleep(0.01)
            generated = self.client.post("/v1/music/generations", json={
                "prompt": "Mandarin pop", "lyrics": readable,
                "provider_options": {"vocal_language": "zh", "conditioning_lyrics": phonetic},
            })

        self.assertEqual(formatted["effective_lyrics"], readable)
        self.assertEqual(formatted["conditioning_lyrics"], phonetic)
        self.assertEqual(generated.status_code, 202)
        self.assertEqual(payloads[-1]["lyrics"], phonetic)
        self.assertEqual(adapter.TASKS["dual-song"]["display_lyrics"], readable)

    def test_conditioning_lyrics_reject_invalid_latin_and_structure_mismatch(self):
        readable = "[Verse 1]\n夜色落在肩上照亮回家的方向\n路灯把影子拉长陪我穿过街巷"
        invalid = self.client.post("/v1/music/generations", json={
            "prompt": "Mandarin pop", "lyrics": readable,
            "provider_options": {"vocal_language": "zh", "conditioning_lyrics": "[zh] garbage words"},
        })
        mismatched = self.client.post("/v1/music/generations", json={
            "prompt": "Mandarin pop", "lyrics": readable,
            "provider_options": {"vocal_language": "zh", "conditioning_lyrics": "[zh] ye4 se4 luo4 zai4 jian1 shang4"},
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(mismatched.status_code, 400)

    def test_draft_asks_the_lm_for_a_whole_song_and_carries_its_style_plan(self):
        calls = []

        def native(path, payload=None, timeout=30):
            self.assertEqual(path, "/v1/create_sample")
            self.assertEqual(timeout, 600)
            calls.append(payload)
            return {
                "code": 200,
                "data": {
                    "caption": "Quiet Mandarin city folk",
                    "lyrics": "[Verse 1]\n夜色落在肩上\n路灯把影子拉长\n\n[Chorus]\n再走一段\n就到家了",
                    "bpm": 77,
                    "keyscale": "E minor",
                    "timesignature": "4",
                    "duration": 296.0,
                    "vocal_language": "zh",
                },
            }

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post(
                "/v1/music/drafts",
                json={"model": "ace", "brief": "深夜加班后独自走回家", "vocal_language": "zh"},
            )
            self.assertEqual(created.status_code, 202)
            task_id = created.json()["id"]
            for _ in range(50):
                result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["object"], "music.draft")
        self.assertEqual(result["prompt"], "Quiet Mandarin city folk")
        self.assertIn("路灯把影子拉长", result["lyrics"])
        self.assertNotIn("conditioning_lyrics", result)
        self.assertEqual(result["duration_seconds"], 296)
        self.assertEqual(
            result["style_plan"], {"bpm": 77, "key_scale": "E minor", "time_signature": "4"}
        )
        self.assertEqual(calls[0]["query"], "深夜加班后独自走回家")
        self.assertFalse(calls[0]["instrumental"])

        self.assertEqual(
            self.client.get(f"/v1/music/formats/{task_id}").json()["error"]["code"],
            "format_not_found",
        )

    def test_draft_rejects_a_vocal_language_on_an_instrumental_brief(self):
        rejected = self.client.post(
            "/v1/music/drafts",
            json={"model": "ace", "brief": "late night drive", "instrumental": True, "vocal_language": "zh"},
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.json()["error"]["code"], "invalid_vocal_language")

        missing = self.client.post("/v1/music/drafts", json={"model": "ace", "brief": ""})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["error"]["code"], "invalid_brief")

    def test_draft_retries_with_native_sampling_when_the_lm_answers_phonetically(self):
        answers = [
            "[Verse 1]\n[zh] ye4 se4 luo4 zai4 jian1 shang4\n[zh] lu4 deng1 ba3 ying3 zi5 la1 chang2",
            "[Verse 1]\n夜色慢慢落在肩上\n路灯把回家的影子拉长\n雨后的街道安静明亮\n[Chorus]\n再走一段就能看见熟悉的窗",
        ]
        calls = []

        def native(path, payload=None, timeout=30):
            calls.append(payload)
            return {"code": 200, "data": {"caption": "Quiet Mandarin city folk", "lyrics": answers.pop(0)}}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post(
                "/v1/music/drafts",
                json={"model": "ace", "brief": "walking home late", "vocal_language": "zh"},
            )
            task_id = created.json()["id"]
            for _ in range(50):
                result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

        self.assertIn("熟悉的窗", result["lyrics"])
        self.assertNotIn("lyrics_romanized", result["warnings"])
        self.assertEqual(answers, [])
        self.assertEqual([call["temperature"] for call in calls], [0.85, 0.85])
        self.assertEqual(
            [call["query"] for call in calls],
            [
                adapter._draft_query({"brief": "walking home late", "vocal_language": "zh"}, 0),
                adapter._draft_query({"brief": "walking home late", "vocal_language": "zh"}, 1),
            ],
        )

    def test_draft_rejects_lyrics_that_stay_phonetic_across_every_attempt(self):
        romanized = "[Verse 1]\n[zh] ye4 se4 luo4 zai4 jian1 shang4\n[zh] lu4 deng1 ba3 ying3 zi5 la1 chang2"
        calls = []

        def native(path, payload=None, timeout=30):
            calls.append(payload)
            return {"code": 200, "data": {"caption": "Quiet Mandarin city folk", "lyrics": romanized}}

        with mock.patch.object(adapter, "_native_json", side_effect=native) as call:
            created = self.client.post(
                "/v1/music/drafts",
                json={"model": "ace", "brief": "walking home late", "vocal_language": "zh"},
            )
            task_id = created.json()["id"]
            for _ in range(50):
                result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                if result["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.01)

        self.assertEqual(call.call_count, adapter.DRAFT_ATTEMPTS)
        self.assertEqual([item["temperature"] for item in calls], [0.85] * adapter.DRAFT_ATTEMPTS)
        self.assertEqual([item["query"] for item in calls], ["walking home late"] * adapter.DRAFT_ATTEMPTS)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "lyrics_script_invalid")

    def test_draft_query_passes_every_language_brief_through_unchanged(self):
        chinese = {"brief": "夜" * 512, "vocal_language": "zh"}
        self.assertEqual(len(adapter._draft_query(chinese, 0)), 512)
        self.assertEqual(adapter._draft_query(chinese, 2), chinese["brief"])
        english = {"brief": "walking home late", "vocal_language": "en"}
        self.assertEqual(adapter._draft_query(english, 1), english["brief"])

    def test_draft_temperature_stays_at_the_user_value(self):
        script = adapter.DraftValidationError("lyrics_script_invalid", "script")
        repetition = adapter.DraftValidationError("lyrics_repetition_invalid", "loop")
        self.assertEqual(adapter._draft_temperature(0.9, 1, script), 0.9)
        self.assertEqual(adapter._draft_temperature(0.9, 4, script), 0.9)
        self.assertEqual(adapter._draft_temperature(0.9, 2, repetition), 0.9)

    def test_draft_fails_when_the_lm_returns_no_lyrics_for_a_vocal_brief(self):
        def native(path, payload=None, timeout=30):
            return {"code": 200, "data": {"caption": "Quiet Mandarin city folk", "lyrics": "   "}}

        with mock.patch.object(adapter, "_native_json", side_effect=native) as call:
            created = self.client.post(
                "/v1/music/drafts",
                json={"model": "ace", "brief": "深夜加班后独自走回家", "vocal_language": "zh"},
            )
            task_id = created.json()["id"]
            for _ in range(50):
                result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                if result["status"] == "failed":
                    break
                time.sleep(0.01)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "draft_failed")
        self.assertEqual(call.call_count, adapter.DRAFT_ATTEMPTS)

    def test_draft_retries_instrumental_placeholder_for_a_vocal_brief(self):
        answers = [
            {"caption": "Clean acoustic pop", "lyrics": "[Instrumental]"},
            {"caption": "Clean acoustic pop", "lyrics": "[Verse 1]\n沿着熟悉街道慢慢走回家\n晚风把一天疲惫轻轻放下\n[Chorus]\n远处那扇窗还为我亮着"},
        ]

        def native(path, payload=None, timeout=30):
            return {"code": 200, "data": answers.pop(0)}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            created = self.client.post(
                "/v1/music/drafts",
                json={"model": "ace", "brief": "写一首回家的歌", "vocal_language": "zh"},
            )
            task_id = created.json()["id"]
            for _ in range(50):
                result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

        self.assertEqual(result["status"], "completed")
        self.assertIn("慢慢走回家", result["lyrics"])
        self.assertEqual(answers, [])

    def test_draft_rejects_latin_gibberish_and_extreme_chinese_repetition(self):
        fixtures = (
            (
                "[Verse 1]\nOh, bua cha te, bua cha te\ntsok ko, tsok ko, all that\nOh, bua cha te, bua cha te\ntsok ko, tsok ko, all that\n[Chorus]\nBí pięk de beat, all that\nBí pięk de beat, all that\nBí pięk de beat, all that\nBí pięk de beat, all that",
                "lyrics_script_invalid",
            ),
            (
                "[Verse 1]\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡\n城市的灯还没有睡",
                "lyrics_repetition_invalid",
            ),
            (
                "[Verse 1]\n霓虹闪烁映在窗上涌动的光\n脚步匆匆っちゃ이向谁在追赶\n心里的热火从未熄灭一半",
                "lyrics_script_invalid",
            ),
            (
                "[Verse 1]\n長安的雨傳染vocal上水袖\n穿過九條河的Inspiration\n讓回憶在晨光中悄然綻放",
                "lyrics_script_invalid",
            ),
            (
                "[Verse 1]\n你什么也说不清\n你已经说得很清清楚楚\nthéwēi yīfān lìch gōng\n因为已经说得很明白\n[Chorus]\n我也不再是懵懂的少年\n今夜沿着灯光慢慢回家\n窗边的人还在等我回答",
                "lyrics_script_invalid",
            ),
        )
        for lyrics, code in fixtures:
            with self.subTest(code=code):
                with mock.patch.object(
                    adapter,
                    "_native_json",
                    return_value={"code": 200, "data": {"caption": "Mandarin pop", "lyrics": lyrics}},
                ) as call:
                    created = self.client.post(
                        "/v1/music/drafts",
                        json={"model": "ace", "brief": "write a coherent city song", "vocal_language": "zh"},
                    )
                    task_id = created.json()["id"]
                    for _ in range(50):
                        result = self.client.get(f"/v1/music/drafts/{task_id}").json()
                        if result["status"] == "failed":
                            break
                        time.sleep(0.01)
                    self.assertEqual(call.call_count, adapter.DRAFT_ATTEMPTS)
                self.assertEqual(result["error"]["code"], code)

    def test_draft_accepts_a_complete_chinese_song_with_a_repeated_chorus(self):
        lyrics = "\n".join([
            "[Verse 1]", "晚风吹过旧街口", "我把影子留在身后", "末班车穿过沉默", "远处有人轻轻唱歌",
            "[Chorus]", "带我回到那盏灯火", "带我回到你的身侧", "今夜不再独自漂泊", "让所有心事慢慢降落",
            "[Verse 2]", "清晨沿着河岸醒来", "雨滴敲开灰色窗台", "昨天已经随风离开", "新的故事正在展开",
            "[Chorus]", "带我回到那盏灯火", "带我回到你的身侧", "今夜不再独自漂泊", "让所有心事慢慢降落",
        ])
        self.assertTrue(adapter._has_expected_chinese_script(lyrics, "zh"))
        self.assertFalse(adapter._has_extreme_repetition(lyrics))
        hook_lyrics = lyrics + "\nHey 让心跳跟上旋律\ntonight\nI love you"
        self.assertTrue(adapter._has_expected_chinese_script(hook_lyrics, "zh"))

    def test_live_consecutive_line_regression_is_extreme_repetition(self):
        lyrics = """[Verse 1]
我和这些年的老朋友
老朋友的酒我们喝到吐
回忆错的我还是要生活
生活生活生活
[Chorus]
生活就是生活
生活就是生活
生活就是生活
生活就是生活
[Bridge]
人生就像梦
人生还是梦
我们追着梦
天亮继续走"""
        self.assertTrue(adapter._has_extreme_repetition(lyrics))

    def test_rejects_character_and_bigram_loops_from_the_live_regression(self):
        fixtures = (
            "[Verse 1]\n診診診診诊断深层夜色",
            "[Verse 1]\n深层深层深层深层回声",
            "[Verse 1]\n灯影灯影灯影灯影灯影",
        )
        for lyrics in fixtures:
            with self.subTest(lyrics=lyrics):
                self.assertTrue(adapter._has_extreme_repetition(lyrics))

    def test_text_and_audio_model_tasks_are_mutually_exclusive(self):
        adapter.TASKS["generation-running"] = {
            "id": "generation-running", "kind": "generation", "status": "running", "created_at": 1,
        }
        draft = self.client.post(
            "/v1/music/drafts",
            json={"model": "ace", "brief": "write a song", "vocal_language": "en"},
        )
        self.assertEqual(draft.status_code, 409)
        self.assertEqual(draft.json()["error"]["code"], "model_task_in_progress")

        adapter.TASKS.clear()
        adapter.TASKS["draft-running"] = {
            "id": "draft-running", "kind": "draft", "status": "running", "created_at": 1,
        }
        generation = self.client.post(
            "/v1/music/generations",
            json={"model": "ace", "prompt": "clean pop", "lyrics": "[Verse 1]\nHome", "duration_seconds": 120},
        )
        self.assertEqual(generation.status_code, 409)
        self.assertEqual(generation.json()["error"]["code"], "model_task_in_progress")

    def test_format_input_trims_native_caption_to_contract_limit(self):
        long_caption = (
            "Clean Mandarin pop with conversational female vocals. "
            "Warm acoustic guitar and rounded bass support a relaxed groove. "
            + "Detailed studio arrangement with separated instruments and gentle dynamics. " * 8
        )

        with mock.patch.object(
            adapter,
            "_native_json",
            return_value={"code": 200, "data": {"caption": long_caption, "lyrics": "[Verse 1]\n回家的路\n\n[Chorus]\n江边的风"}},
        ):
            created = self.client.post(
                "/v1/music/formats",
                json={
                    "model": "ace",
                    "prompt": "Mandarin pop",
                    "lyrics": "[Verse 1]\n回家的路\n\n[Chorus]\n江边的风",
                    "vocal_language": "zh",
                    "duration_seconds": 240,
                },
            )
            task_id = created.json()["id"]
            result = created.json()
            for _ in range(50):
                result = self.client.get(f"/v1/music/formats/{task_id}").json()
                if result["status"] == "completed":
                    break
                time.sleep(0.01)

        self.assertEqual(result["status"], "completed")
        self.assertLessEqual(len(result["effective_prompt"]), 512)
        self.assertTrue(result["effective_prompt"].endswith("."))
        self.assertIn("formatted_caption_trimmed_to_512_characters", result["warnings"])

    def test_chinese_format_metrics_flag_repeated_sentence_openings(self):
        warnings, metrics = adapter._line_metrics(
            "[Verse 1]\n我走过旧街\n我记得那场雨\n我想起你的话\n我看见天亮了",
            "zh",
        )
        self.assertEqual(metrics["syntactic_pattern_risk"], "high")
        self.assertIn("repetitive_chinese_line_openings", warnings)

    def test_quality_profiles_use_xl_sft_without_repeating_structure_in_caption(self):
        payloads = []

        def native(path, payload=None):
            self.assertEqual(path, "/release_task")
            payloads.append(payload)
            return {"code": 200, "data": {"task_id": f"task-{len(payloads)}"}}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            quality = self.client.post(
                "/v1/music/generations",
                json={
                    "prompt": "Mandarin pop",
                    "duration_seconds": 180,
                    "provider_options": {
                        "quality_profile": "quality",
                        "bpm": 92,
                        "key_scale": "D major",
                        "time_signature": "4",
                        "vocal_language": "zh",
                        "vocal_type": "warm female lead",
                        "section_structure": "intro, verse, chorus, bridge, chorus, outro",
                    },
                },
            )
            fast = self.client.post(
                "/v1/music/generations",
                json={"prompt": "pop", "provider_options": {"quality_profile": "fast"}},
            )

        self.assertEqual(quality.status_code, 202)
        self.assertEqual(payloads[0]["model"], "acestep-v15-xl-sft")
        self.assertEqual(payloads[0]["inference_steps"], 50)
        self.assertEqual(payloads[0]["guidance_scale"], 7.0)
        self.assertEqual(payloads[0]["shift"], 1.0)
        self.assertFalse(payloads[0]["use_adg"])
        self.assertFalse(payloads[0]["use_cot_caption"])
        self.assertFalse(payloads[0]["use_cot_lyrics"])
        self.assertFalse(payloads[0]["use_format"])
        self.assertIn("background hiss", payloads[0]["lm_negative_prompt"])
        self.assertEqual(payloads[0]["bpm"], 92)
        self.assertIn("Vocal character: warm female lead", payloads[0]["prompt"])
        self.assertNotIn("Song structure:", payloads[0]["prompt"])
        self.assertEqual(fast.status_code, 400)
        self.assertEqual(fast.json()["error"]["code"], "invalid_quality_profile")
        self.assertEqual(len(payloads), 1)

        adapter.TASKS.clear()
        with mock.patch.object(adapter, "_native_json", side_effect=native):
            high = self.client.post(
                "/v1/music/generations",
                json={"prompt": "Mandarin pop", "provider_options": {"quality_profile": "high_quality"}},
            )
        self.assertEqual(high.status_code, 202)
        self.assertEqual(payloads[1]["model"], "acestep-v15-xl-sft")
        self.assertEqual(payloads[1]["inference_steps"], 64)
        self.assertTrue(payloads[1]["use_adg"])
        self.assertEqual(payloads[1]["guidance_scale"], 8.0)
        self.assertEqual(payloads[1]["shift"], 3.0)

    def test_clean_and_textured_production_and_caption_modes(self):
        payloads = []

        def native(path, payload=None):
            self.assertEqual(path, "/release_task")
            payloads.append(payload)
            return {"code": 200, "data": {"task_id": f"task-{len(payloads)}"}}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            clean = self.client.post(
                "/v1/music/generations",
                json={"prompt": "polished Mandarin pop", "provider_options": {"production_profile": "clean", "caption_mode": "preserve"}},
            )
            adapter.TASKS.clear()
            textured = self.client.post(
                "/v1/music/generations",
                json={"prompt": "lo-fi rainy folk", "provider_options": {"production_profile": "textured", "caption_mode": "enhance"}},
            )

        self.assertEqual(clean.status_code, 202)
        self.assertFalse(payloads[0]["use_cot_caption"])
        self.assertIn("clean studio recording", payloads[0]["prompt"])
        self.assertIn("background hiss", payloads[0]["lm_negative_prompt"])
        self.assertEqual(textured.status_code, 202)
        self.assertTrue(payloads[1]["use_cot_caption"])
        self.assertNotIn("lm_negative_prompt", payloads[1])
        self.assertNotIn("clean studio recording", payloads[1]["prompt"])

    def test_full_caption_is_preserved_when_adapter_details_do_not_fit(self):
        payloads = []

        def native(path, payload=None):
            payloads.append(payload)
            return {"code": 200, "data": {"task_id": "task-full-caption"}}

        caption = "A" * 512
        with mock.patch.object(adapter, "_native_json", side_effect=native):
            response = self.client.post(
                "/v1/music/generations",
                json={
                    "prompt": caption,
                    "provider_options": {
                        "production_profile": "clean",
                        "caption_mode": "preserve",
                        "vocal_type": "warm female lead",
                    },
                },
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(payloads[0]["prompt"], caption)
        self.assertIn("background hiss", payloads[0]["lm_negative_prompt"])

    def test_rejects_overlong_vocal_type(self):
        response = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"vocal_type": "v" * 121}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_provider_options")

    def test_accepts_all_official_vocal_languages_and_rejects_unknown_codes(self):
        payloads = []

        def native(path, payload=None):
            payloads.append(payload)
            return {"code": 200, "data": {"task_id": f"language-{len(payloads)}"}}

        with mock.patch.object(adapter, "_native_json", side_effect=native):
            for language in adapter.VOCAL_LANGUAGES:
                response = self.client.post(
                    "/v1/music/generations",
                    json={"prompt": "clean studio song", "provider_options": {"vocal_language": language}},
                )
                self.assertEqual(response.status_code, 202, language)
                self.assertEqual(payloads[-1]["vocal_language"], language)
                adapter.TASKS.clear()

        invalid = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"vocal_language": "xx"}},
        )
        vocal_unknown = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"vocal_language": "unknown"}},
        )
        self.assertEqual(invalid.json()["error"]["code"], "invalid_vocal_language")
        self.assertEqual(vocal_unknown.json()["error"]["code"], "invalid_vocal_language")
        adapter.TASKS.clear()
        with mock.patch.object(adapter, "_native_json", side_effect=native):
            instrumental_unknown = self.client.post(
                "/v1/music/generations",
                json={"prompt": "instrumental score", "instrumental": True, "provider_options": {"vocal_language": "unknown"}},
            )
        self.assertEqual(instrumental_unknown.status_code, 202)

    def test_repaint_decodes_audio_and_maps_native_range(self):
        payloads = []

        def native(path, payload=None):
            self.assertEqual(path, "/release_task")
            payloads.append(payload)
            return {"code": 200, "data": {"task_id": "repaint-1"}}

        with mock.patch.object(adapter, "_native_json", side_effect=native), mock.patch.object(
            adapter, "REPAINT_INPUT_DIR", str(self.temp_dir)
        ):
            response = self.client.post(
                "/v1/music/generations",
                json={
                    "operation": "repaint",
                    "prompt": "Mandarin indie pop with a clean vocal pickup",
                    "input_audio": "data:audio/wav;base64," + base64.b64encode(b"RIFFaudio").decode(),
                    "duration_seconds": 240,
                    "provider_options": {"repaint_start_seconds": 32, "repaint_end_seconds": 48},
                },
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(payloads[0]["task_type"], "repaint")
        self.assertEqual(payloads[0]["repainting_start"], 32)
        self.assertEqual(payloads[0]["repainting_end"], 48)
        self.assertTrue(payloads[0]["src_audio_path"].startswith(str(self.temp_dir)))

    def test_rejects_invalid_quality_controls(self):
        profile = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"quality_profile": "ultra"}},
        )
        guidance = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"guidance_scale": 12}},
        )
        unknown = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"magic": True}},
        )
        production = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"production_profile": "dusty"}},
        )
        caption = self.client.post(
            "/v1/music/generations",
            json={"prompt": "pop", "provider_options": {"caption_mode": "rewrite"}},
        )
        self.assertEqual(profile.status_code, 400)
        self.assertEqual(profile.json()["error"]["code"], "invalid_quality_profile")
        self.assertEqual(guidance.status_code, 400)
        self.assertEqual(guidance.json()["error"]["code"], "invalid_guidance_scale")
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.json()["error"]["code"], "unknown_provider_option")
        self.assertEqual(production.json()["error"]["code"], "invalid_production_profile")
        self.assertEqual(caption.json()["error"]["code"], "invalid_caption_mode")


if __name__ == "__main__":
    unittest.main()
