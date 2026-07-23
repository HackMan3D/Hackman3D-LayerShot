APP_STYLE = """
* { font-family: "Inter", "Segoe UI", "Arial"; font-size: 14px; color: #f5f7fb; }
QMainWindow, QWidget { background: #101218; }
QLabel { background: transparent; }
QFrame#topbar { background: #171a22; border-bottom: 1px solid #292e3a; }
QFrame#support { background: #13283e; border: 1px solid #245a88; border-radius: 10px; }
QFrame#community { background: #1b1e24; border: 1px solid #383b44; border-radius: 16px; }
QFrame#sidebar { background: #151820; border-right: 1px solid #292e3a; }
QFrame#card { background: #1b1e27; border: 1px solid #303541; border-radius: 14px; }
QLabel#brand { font-size: 21px; font-weight: 800; }
QLabel#communityTitle { color: #72c6ff; font-size: 17px; font-weight: 800; }
QLabel#supportCopy { color: #b9bac0; font-size: 15px; }
QLabel#footer { color: #74767e; font-weight: 600; }
QLabel#printerName { font-size: 24px; font-weight: 800; }
QLabel#printerMeta, QLabel#filename { color: #a4a5aa; font-size: 15px; }
QLabel#metricLabel { color: #9b9ca2; font-size: 13px; }
QLabel#metricValue { font-size: 21px; font-weight: 800; }
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
QPushButton#danger { background: #44282b; border-color: #5b3034; }
QPushButton#nav { text-align: left; border: 0; background: transparent; padding: 12px 16px; }
QPushButton#nav:hover { background: #202633; }
QPushButton#nav:checked { background: #173b62; color: white; }
QLineEdit, QComboBox, QSpinBox { background: #101218; border: 1px solid #3a404e;
                                border-radius: 7px; padding: 8px; min-height: 20px; }
QComboBox { padding-right: 38px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right;
                       width: 38px; border: 0; background: transparent; }
QComboBox::down-arrow { image: url("__DROPDOWN_ARROW__"); width: 16px; height: 10px; }
QComboBox QAbstractItemView { background: #171a22; border: 1px solid #3a404e;
                              border-radius: 8px; padding: 5px; selection-background-color: #173b62; }
QToolTip { background: #242936; color: white; border: 1px solid #4a5263; padding: 6px; }
QPushButton#social { min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px;
                     padding: 3px; border-radius: 8px; }
QScrollArea { border: 0; }
QFrame#metric { background: #131419; border: 0; border-radius: 10px; }
QProgressBar { background: #101218; border: 0; border-radius: 5px; height: 10px; }
QProgressBar::chunk { background: #1684f8; border-radius: 5px; }
"""
