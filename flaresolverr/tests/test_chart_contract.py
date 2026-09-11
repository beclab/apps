import pathlib
import unittest


CHART_ROOT = pathlib.Path(__file__).parents[1]
I18N_LOCALES = ("de-DE", "en-US", "es-ES", "fr-FR", "it-IT", "ja-JP", "zh-CN")


class ChartContractTest(unittest.TestCase):
    def test_chart_and_manifest_versions_match_v350(self):
        chart = (CHART_ROOT / "Chart.yaml").read_text(encoding="utf-8")
        manifest = (CHART_ROOT / "OlaresManifest.yaml").read_text(encoding="utf-8")
        self.assertIn("name: flaresolverr", chart)
        self.assertIn("version: 1.0.17", chart)
        self.assertIn("appVersion: 3.5.0", chart)
        self.assertIn("version: '1.0.17'", manifest)
        self.assertIn("versionName: '3.5.0'", manifest)
        self.assertIn("flaresolverr/flaresolverr:v3.5.0", manifest)

    def test_official_image_and_recreate_rollout(self):
        deployment = (CHART_ROOT / "templates" / "deployment.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'image: "docker.io/flaresolverr/flaresolverr:v3.5.0"', deployment
        )
        self.assertIn("type: Recreate", deployment)
        self.assertIn("runAsUser: 1000", deployment)
        self.assertIn("containerPort: 8191", deployment)
        self.assertIn("targetPort: 8191", deployment)
        self.assertIn("path: /", deployment)
        self.assertNotIn("beclab/flaresolverr", deployment)

    def test_client_proxy_forwards_to_solver_port(self):
        proxy = (CHART_ROOT / "templates" / "clientproxy.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("listen 8080;", proxy)
        self.assertIn("proxy_pass http://flaresolverr:8191;", proxy)

    def test_upgrade_notes_cover_all_locales(self):
        for locale in I18N_LOCALES:
            notes = (
                CHART_ROOT / "i18n" / locale / "OlaresManifest.yaml"
            ).read_text(encoding="utf-8")
            self.assertIn("v3.5.0", notes, locale)
            self.assertIn("flaresolverr/flaresolverr:v3.5.0", notes, locale)


if __name__ == "__main__":
    unittest.main()
