#!/usr/bin/env python3
"""Translation consistency tests."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translations import TRANSLATIONS


def _extract_used_translation_keys() -> set[str]:
    """Extract all app.t("key") usages from project files."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    key_pattern = re.compile(r"app\.t\(\s*['\"]([^'\"]+)['\"]\s*\)")
    used_keys: set[str] = set()

    for root, _, files in os.walk(project_root):
        if "/translations" in root or "/tests" in root or "__pycache__" in root:
            continue

        for filename in files:
            if not filename.endswith(".py"):
                continue

            file_path = os.path.join(root, filename)
            with open(file_path, encoding="utf-8") as file_obj:
                content = file_obj.read()

            used_keys.update(key_pattern.findall(content))

    return used_keys


class TestTranslations(unittest.TestCase):
    """Validate translation dictionaries for all supported languages."""

    def test_all_languages_match_english_keys(self):
        """All language dictionaries must match English key set exactly."""
        english_keys = set(TRANSLATIONS["English"].keys())

        for language, language_dict in TRANSLATIONS.items():
            language_keys = set(language_dict.keys())
            self.assertEqual(
                language_keys,
                english_keys,
                msg=(
                    f"{language} translation keys mismatch. "
                    f"Missing: {sorted(english_keys - language_keys)} | "
                    f"Extra: {sorted(language_keys - english_keys)}"
                ),
            )

    def test_all_used_app_t_keys_exist_in_all_languages(self):
        """Every app.t key used in code must exist in every language."""
        used_keys = _extract_used_translation_keys()

        for language, language_dict in TRANSLATIONS.items():
            language_keys = set(language_dict.keys())
            missing = sorted(used_keys - language_keys)
            self.assertFalse(
                missing,
                msg=f"{language} is missing used keys: {missing}",
            )


if __name__ == "__main__":
    unittest.main()
