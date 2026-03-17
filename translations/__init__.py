"""
madOS Installer - Translation loader
Combines all language translations into a single TRANSLATIONS dict
"""

import importlib
import os

TRANSLATIONS = {}

translations_dir = os.path.dirname(os.path.abspath(__file__))

for filename in os.listdir(translations_dir):
    if filename.endswith(".py") and filename not in ("__init__.py", "__pycache__"):
        lang_code = filename[:-3]
        module = importlib.import_module(f"translations.{lang_code}")
        if hasattr(module, "TRANSLATIONS"):
            TRANSLATIONS.update(module.TRANSLATIONS)
