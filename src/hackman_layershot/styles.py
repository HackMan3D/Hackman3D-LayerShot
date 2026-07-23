APP_STYLE = """
* { font-family: "Inter", "Segoe UI", "Arial"; font-size: 14px; color: #f5f7fb; }
QMainWindow, QWidget { background: #101218; }
QLabel { background: transparent; }
QFrame#topbar { background: #171a22; border-bottom: 1px solid #292e3a; }
QFrame#support { background: #13283e; border: 1px solid #245a88; border-radius: 10px; }
QFrame#sidebar { background: #151820; border-right: 1px solid #292e3a; }
QFrame#card { background: #1b1e27; border: 1px solid #303541; border-radius: 14px; }
QLabel#brand { font-size: 21px; font-weight: 800; }
QLabel#title { font-size: 29px; font-weight: 800; }
QLabel#subtitle { color: #9ea6b7; }
QLabel#section { font-size: 18px; font-weight: 700; }
QLabel#good { color: #3ddc97; font-weight: 700; }
QLabel#bad { color: #ff6b6b; font-weight: 700; }
QPushButton { background: #292e3a; border: 1px solid #3c4352; border-radius: 8px;
              padding: 9px 14px; font-weight: 650; }
QPushButton:hover { background: #353b49; }
QPushButton#primary { background: #1684f8; border-color: #1684f8; }
QPushButton#primary:hover { background: #3294ff; }
QPushButton#nav { text-align: left; border: 0; background: transparent; padding: 12px 16px; }
QPushButton#nav:hover { background: #202633; }
QPushButton#nav:checked { background: #173b62; color: white; }
QLineEdit, QComboBox, QSpinBox { background: #101218; border: 1px solid #3a404e;
                                border-radius: 7px; padding: 8px; min-height: 20px; }
QComboBox::drop-down { border: 0; width: 24px; }
QScrollArea { border: 0; }
QProgressBar { background: #101218; border: 0; border-radius: 5px; height: 10px; }
QProgressBar::chunk { background: #1684f8; border-radius: 5px; }
"""
