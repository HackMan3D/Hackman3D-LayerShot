import sys
from . import __version__
from .main_window import MainWindow
from .qt_compat import QApplication, QIcon, application_exec
from .services import asset_path
from .styles import APP_STYLE

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Hackman3D LayerShot")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("HackMan3D")
    app.setQuitOnLastWindowClosed(True)
    icon = asset_path("Hackman3DLayerShot.png")
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    app.setStyleSheet(APP_STYLE.replace(
        "__DROPDOWN_ARROW__", str(asset_path("dropdown_arrow.svg"))))
    window = MainWindow()
    window.show()
    raise SystemExit(application_exec(app))

if __name__ == "__main__":
    main()
