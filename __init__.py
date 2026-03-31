"""madOS Installer - GTK Edition."""

# Import MadOSInstaller directly from the package's app module
# This works because when the package is imported, app.py is in the package namespace
import mados_installer.app
MadOSInstaller = mados_installer.app.MadOSInstaller

__app_name__ = "madOS Installer"
__version__ = "1.0.0"
