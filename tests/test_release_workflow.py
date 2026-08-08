from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release-binaries.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_version_tags_trigger_the_workflow(self):
        self.assertIn("push:", self.workflow)
        self.assertIn('      - "v*"', self.workflow)
        self.assertIn("github.ref_name", self.workflow)

    def test_tests_run_before_platform_builds(self):
        self.assertIn("python -m unittest discover -s tests -v", self.workflow)
        self.assertIn("needs: test", self.workflow)
        self.assertIn("Validate tag matches application version", self.workflow)

    def test_both_release_binaries_are_built_from_spec(self):
        self.assertIn("windows-2022", self.workflow)
        self.assertIn("ubuntu-22.04", self.workflow)
        self.assertIn('python-version: "3.11.9"', self.workflow)
        self.assertIn("MoviuPrintServer-Windows-x86_64.exe", self.workflow)
        self.assertIn("MoviuPrintServer-Linux-x86_64", self.workflow)
        self.assertIn("PyInstaller --clean --noconfirm MoviuPrintServer.spec", self.workflow)

    def test_release_is_created_with_generated_notes(self):
        self.assertIn('gh release create "$RELEASE_TAG"', self.workflow)
        self.assertIn("--generate-notes", self.workflow)
        self.assertIn('gh release upload "$RELEASE_TAG" artifacts/* --clobber', self.workflow)


if __name__ == "__main__":
    unittest.main()
