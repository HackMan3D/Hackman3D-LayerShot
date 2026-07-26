"""Small Qt binding bridge for the Windows x86 compatibility build."""

try:
    from PySide6.QtCore import (
        QObject, QRunnable, QSettings, QSize, QThreadPool, QTimer, Qt, Signal,
        QUrl,
    )
    from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap, QTransform
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
        QPushButton, QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
    )
    QT_BINDING = "PySide6"
except ImportError:
    from PySide2.QtCore import (
        QObject, QRunnable, QSettings, QSize, QThreadPool, QTimer, Qt, Signal,
        QUrl,
    )
    from PySide2.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap, QTransform
    from PySide2.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
        QPushButton, QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
    )
    QT_BINDING = "PySide2"


def application_exec(application):
    runner = getattr(application, "exec", None)
    return runner() if runner else application.exec_()
