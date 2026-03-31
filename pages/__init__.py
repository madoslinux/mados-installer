"""
madOS Installer - Pages package
"""

from pages.welcome import create_welcome_page
from pages.disk import create_disk_page
from pages.partitioning import create_partitioning_page
from pages.user import create_user_page
from pages.locale import create_locale_page
from pages.summary import create_summary_page
from pages.installation import create_installation_page
from pages.completion import create_completion_page

__all__ = [
    "create_welcome_page",
    "create_disk_page",
    "create_partitioning_page",
    "create_user_page",
    "create_locale_page",
    "create_summary_page",
    "create_installation_page",
    "create_completion_page",
]
