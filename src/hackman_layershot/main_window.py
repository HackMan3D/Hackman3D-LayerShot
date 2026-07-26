import json, os, platform, re, shutil, subprocess, sys, time
from ctypes import c_void_p
from pathlib import Path
from .qt_compat import (
    QT_BINDING, QColor, QDesktopServices, QIcon, QImageReader, QPainter,
    QPixmap, QTransform, QObject, QRunnable, QSettings,
    QSize, QThreadPool, QTimer, Qt, Signal, QUrl,
    QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget
)
from . import __version__
from .services import asset_path, discover_esps, discover_printers, esp_post, esp_status, hidden_subprocess_kwargs, known_wifi_networks, known_wifi_password, latest_layershot_release, printer_status, save_wifi_password, serial_ports
from .translations import LANGUAGES, tr

MODELS = ["K2 Plus", "K2", "K1 Max", "K1C", "K1", "Ender-3 V3 Plus",
          "Ender-3 V3", "Ender-3 V3 KE", "Ender-3 V3 SE", "Hi", "Hi Combo",
          "SparkX i7", "Other Moonraker / Klipper"]
CAMERA_TARGETS = (
    ("camera_iphone", "iphone"),
    ("camera_android", "android"),
    ("camera_hid_volume_up", "hid_volume_up"),
    ("camera_hid_volume_down", "hid_volume_down"),
    ("camera_hid_enter", "hid_enter"),
    ("camera_hid_space", "hid_space"),
    ("camera_dji", "dji"),
    ("camera_gopro", "gopro"),
    ("camera_insta360", "insta360"),
)
SUPPORTED_IMAGE_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff",
    ".bmp",
}

class CameraView(QWidget):
    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host, self.port, self.web_view = host, port, None
        if platform.system() == "Darwin":
            self.setAttribute(Qt.WA_NativeWindow)
        self.setMinimumHeight(300)

    def showEvent(self, event):
        super().showEvent(event)
        if self.web_view is None:
            QTimer.singleShot(0, self.create_web_view)

    def create_web_view(self):
        camera_url = f"http://{self.host}:{self.port}/camera.html"
        if platform.system() == "Darwin":
            import objc, WebKit
            from Foundation import NSURL, NSURLRequest
            native_view = objc.objc_object(c_void_p=int(self.winId()))
            self.web_view = WebKit.WKWebView.alloc().initWithFrame_(native_view.bounds())
            self.web_view.setAutoresizingMask_(18)
            native_view.addSubview_(self.web_view)
            url = NSURL.URLWithString_(camera_url)
            self.web_view.loadRequest_(NSURLRequest.requestWithURL_(url))
        else:
            import importlib
            QWebEngineView = importlib.import_module(
                f"{QT_BINDING}.QtWebEngineWidgets").QWebEngineView
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.web_view = QWebEngineView(self)
            layout.addWidget(self.web_view)
            self.web_view.setUrl(QUrl(camera_url))

class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)

class Worker(QRunnable):
    def __init__(self, fn, *args):
        super().__init__(); self.fn, self.args, self.signals = fn, args, WorkerSignals()
    def run(self):
        try: self.signals.done.emit(self.fn(*self.args))
        except Exception as exc: self.signals.failed.emit(str(exc))

def button(text, slot=None, primary=False):
    b = QPushButton(text)
    if primary: b.setObjectName("primary")
    if slot: b.clicked.connect(slot)
    return b

def social_button(asset, name, url, opener):
    b = QPushButton()
    b.setObjectName("social")
    b.setIcon(QIcon(str(asset_path(asset))))
    b.setIconSize(QSize(23, 23))
    b.setToolTip(name)
    b.setAccessibleName(name)
    b.clicked.connect(lambda checked=False: opener(url))
    return b

def card():
    f = QFrame(); f.setObjectName("card"); f.setLayout(QVBoxLayout())
    f.layout().setContentsMargins(20, 18, 20, 18); f.layout().setSpacing(12)
    return f

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.closing = False
        self.settings = QSettings()
        self.lang = self.settings.value("language", "en")
        self.printers = json.loads(self.settings.value("printers", "[]"))
        self.active_printer_id = str(
            self.settings.value("active_printer_id", ""))
        self.camera_target_value = self.settings.value("camera_target", "iphone")
        self.pool = QThreadPool.globalInstance()
        self.active_workers = set()
        self.cards = {}
        self.camera_views = {}
        self.camera_step_confirmed = False
        self.firmware_ready = str(
            self.settings.value("firmware_installed", "false")
        ).lower() in ("1", "true", "yes")
        self.setWindowTitle(f"Hackman3D LayerShot — {__version__}")
        self.setMinimumSize(1050, 720); self.resize(1240, 820)
        self._build()
        self._refresh_printer_cards()
        self.poller = QTimer(self); self.poller.timeout.connect(self.refresh_all)
        self.poller.timeout.connect(self.refresh_esp_status); self.poller.start(5000)
        QTimer.singleShot(1500, self.check_for_updates)
        QTimer.singleShot(800, self.detect_existing_esp)

    def T(self, key): return tr(self.lang, key)
    def open_url(self, url): QDesktopServices.openUrl(QUrl(url))
    def label(self, text, kind=None):
        w = QLabel(text); w.setWordWrap(True)
        if kind: w.setObjectName(kind)
        return w

    def _build(self):
        root = QWidget(); outer = QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        nav = QFrame(); nav.setObjectName("sidebar"); nav.setFixedWidth(270); nv = QVBoxLayout(nav)
        nv.setContentsMargins(24,28,24,28); nv.setSpacing(18)
        brand_row = QHBoxLayout()
        logo = QLabel(); logo.setFixedSize(64,64)
        icon = asset_path("Hackman3DLayerShot.png")
        if icon.exists():
            logo.setPixmap(QPixmap(str(icon)).scaled(64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        brand_row.addWidget(logo); brand_row.addWidget(self.label("Hackman3D\nLayerShot", "brand"), 1)
        nv.addLayout(brand_row)
        self.language = QComboBox(); self.language.setMinimumWidth(210)
        self.language.setToolTip("Choisir la langue" if self.lang == "fr" else "Choose language")
        self.language.setAccessibleName("Language selection menu")
        for name, code in LANGUAGES: self.language.addItem(name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(self.lang)))
        self.language.currentIndexChanged.connect(self.change_language); nv.addWidget(self.language)
        nv.addSpacing(12)
        self.nav_buttons = []
        for key in ("printers","setup","esp","timelapse","about"):
            b = button(self.T(key)); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False, i=len(self.nav_buttons): self.show_page(i))
            self.nav_buttons.append(b); nv.addWidget(b)
        nv.addStretch(); nv.addWidget(self.label("●  "+self.T("ready_configure"), "subtitle"))

        content = QWidget(); content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32,28,32,18); content_layout.setSpacing(18)
        community = QFrame(); community.setObjectName("community")
        community_layout = QVBoxLayout(community); community_layout.setContentsMargins(18,16,18,16)
        community_top = QHBoxLayout()
        community_top.addWidget(self.label("Hackman3D", "communityTitle"))
        community_top.addStretch()
        for asset, text, url in [
            ("social_creality.svg","Creality Cloud","https://www.crealitycloud.com/user/5221417142"),
            ("social_tiktok.svg","TikTok","https://tiktok.com/@hackman3d"),
            ("social_instagram.svg","Instagram","https://www.instagram.com/hackman_3dprint/"),
            ("social_youtube.svg","YouTube","https://youtube.com/@hackman3d"),
            ("social_email.svg","Feedback","mailto:hackman3d.pro@gmail.com"),
        ]:
            community_top.addWidget(social_button(asset, text, url, self.open_url))
        community_layout.addLayout(community_top)
        support_row = QHBoxLayout()
        support_copy = self.label(self.T("support_long"), "supportCopy")
        support_copy.setWordWrap(True); support_row.addWidget(support_copy, 1)
        feedback = button(self.T("feedback_button"), lambda: self.open_url("mailto:hackman3d.pro@gmail.com"))
        feedback.setIcon(QIcon(str(asset_path("social_email.svg"))))
        donate = button(self.T("support_project"), lambda: self.open_url("https://paypal.me/hackman3d"), True)
        donate.setIcon(QIcon(str(asset_path("social_paypal.svg"))))
        support_row.addWidget(feedback); support_row.addWidget(donate)
        community_layout.addLayout(support_row); content_layout.addWidget(community)
        self.update_banner = QFrame()
        self.update_banner.setObjectName("support")
        update_layout = QHBoxLayout(self.update_banner)
        self.update_message = self.label("", "good")
        self.update_button = button(self.T("download_update"), primary=True)
        update_layout.addWidget(self.update_message, 1)
        update_layout.addWidget(self.update_button)
        self.update_banner.hide()
        content_layout.addWidget(self.update_banner)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_printers_page()); self.stack.addWidget(self.build_setup_page())
        self.stack.addWidget(self.build_esp_page()); self.stack.addWidget(self.build_timelapse_page())
        self.stack.addWidget(self.build_about_page())
        content_layout.addWidget(self.stack, 1)
        footer = self.label(
            f"{self.T('footer')} · {self.T('version')} {__version__}",
            "footer")
        footer.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(footer)
        outer.addWidget(nav); outer.addWidget(content, 1)
        self.setCentralWidget(root); self.show_page(0)

    def page_shell(self, title):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); lay = QVBoxLayout(content); lay.setContentsMargins(36,28,36,36); lay.setSpacing(18)
        lay.addWidget(self.label(title, "title")); scroll.setWidget(content)
        return scroll, lay

    def build_printers_page(self):
        page, lay = self.page_shell(self.T("printers"))
        actions = QHBoxLayout(); actions.addWidget(button(self.T("refresh"), self.refresh_all, True))
        actions.addStretch(); actions.addWidget(button(self.T("add"), lambda: self.show_page(1)))
        lay.addLayout(actions)
        self.printer_grid_host = QWidget(); self.printer_grid = QGridLayout(self.printer_grid_host)
        self.printer_grid.setSpacing(16); lay.addWidget(self.printer_grid_host); lay.addStretch()
        return page

    def build_setup_page(self):
        page, lay = self.page_shell(self.T("setup_title"))
        self.setup_progress = self.label(self.T("setup_start"), "supportCopy")
        lay.addWidget(self.setup_progress)
        p = card(); p.layout().addWidget(self.label(self.T("printer_step"), "section"))
        self.setup_printer_card = p
        form = QFormLayout()
        self.p_name = QLineEdit(); self.p_name.setPlaceholderText("Workshop K2")
        self.p_model = QComboBox(); self.p_model.addItems(MODELS)
        self.p_host = QLineEdit(); self.p_host.setPlaceholderText("192.0.2.51")
        self.p_port = QSpinBox(); self.p_port.setRange(1,65535); self.p_port.setValue(4408)
        for key,w in [("name",self.p_name),("model",self.p_model),("address",self.p_host),("port",self.p_port)]:
            form.addRow(self.T(key),w)
        p.layout().addLayout(form)
        discovery = QHBoxLayout()
        self.discovered_printers = QComboBox()
        self.discovered_printers.setMinimumWidth(390)
        self.discovered_printers.addItem(self.T("no_discovered_printer"), None)
        self.discovered_printers.currentIndexChanged.connect(self.select_discovered_printer)
        for saved_printer in self.printers:
            label = (f"{saved_printer['name']} — {saved_printer['model']} — "
                     f"{saved_printer['host']}:{saved_printer['port']}")
            self.discovered_printers.addItem(label, saved_printer)
            if saved_printer.get("id") == self.active_printer_id:
                self.discovered_printers.setCurrentIndex(
                    self.discovered_printers.count() - 1)
        self.discovery_button = button(self.T("scan_network"), self.scan_printers)
        discovery.addWidget(self.discovered_printers, 1)
        discovery.addWidget(self.discovery_button)
        p.layout().addLayout(discovery)
        pr = QHBoxLayout(); pr.addWidget(button(self.T("test"), self.test_printer)); pr.addWidget(button(self.T("save"), self.save_printer, True)); pr.addStretch()
        p.layout().addLayout(pr); self.test_result = self.label(""); p.layout().addWidget(self.test_result); lay.addWidget(p)
        w = card(); w.layout().addWidget(self.label(self.T("wifi_step"), "section")); wf = QFormLayout()
        self.setup_wifi_card = w
        self.ssid = QComboBox(); self.ssid.setEditable(True); self.ssid.addItems(known_wifi_networks())
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        password_row = QHBoxLayout(); password_row.setSpacing(8)
        password_row.addWidget(self.password, 1)
        self.password_visibility = button("👁", self.toggle_wifi_password)
        self.password_visibility.setCheckable(True); self.password_visibility.setFixedWidth(46)
        self.password_visibility.setToolTip(self.T("show_password"))
        password_row.addWidget(self.password_visibility)
        password_row.addWidget(button(self.T("use_saved_password"), self.load_known_wifi_password))
        saved_esp_host = str(
            self.settings.value("esp_host", "hackman-layershot.local")).strip()
        if saved_esp_host in (
                "hackman-layershot.lan", "hackman-layershot-001.lan"):
            saved_esp_host = "hackman-layershot.local"
            self.settings.setValue("esp_host", saved_esp_host)
        self.esp_host = QLineEdit(saved_esp_host)
        wf.addRow(self.T("ssid"),self.ssid); wf.addRow(self.T("password"),password_row); wf.addRow(self.T("esp_address"),self.esp_host)
        w.layout().addLayout(wf)
        w.layout().addWidget(self.label(self.T("wifi_24_tip"), "good"))
        lay.addWidget(w)
        camera = card()
        self.setup_camera_card = camera
        camera.layout().addWidget(self.label(self.T("camera_step"), "section"))
        camera_form = QFormLayout()
        self.camera_target = QComboBox()
        for translation_key, value in CAMERA_TARGETS:
            self.camera_target.addItem(self.T(translation_key), value)
        selected_camera = self.camera_target.findData(self.camera_target_value)
        self.camera_target.setCurrentIndex(selected_camera if selected_camera >= 0 else 0)
        self.camera_target.currentIndexChanged.connect(self.camera_target_changed)
        camera_form.addRow(self.T("camera_used"), self.camera_target)
        self.shutter_delay = QComboBox()
        for seconds in range(1, 6):
            self.shutter_delay.addItem(f"{seconds} s", seconds * 1000)
        saved_delay = int(self.settings.value("shutter_delay_ms", 3000))
        closest_delay = min(
            range(self.shutter_delay.count()),
            key=lambda index: abs(
                self.shutter_delay.itemData(index) - saved_delay))
        self.shutter_delay.setCurrentIndex(closest_delay)
        self.shutter_delay.currentIndexChanged.connect(
            self.shutter_delay_changed)
        camera_form.addRow(self.T("shutter_delay"), self.shutter_delay)
        camera.layout().addLayout(camera_form)
        camera.layout().addWidget(self.label(self.T("shutter_delay_tip"), "subtitle"))
        self.camera_compatibility = self.label("", "good")
        self.camera_compatibility.setWordWrap(True)
        camera.layout().addWidget(self.camera_compatibility)
        self.install_pairing_guide = self.label("", "supportCopy")
        camera.layout().addWidget(self.install_pairing_guide)
        self.camera_confirm_button = button(
            self.T("confirm_camera"), self.confirm_camera_step, True)
        camera.layout().addWidget(
            self.camera_confirm_button, 0, Qt.AlignLeft)
        lay.addWidget(camera)

        e = card(); e.layout().addWidget(self.label(self.T("esp_step"), "section"))
        self.setup_flash_card = e
        ef = QFormLayout(); self.port_combo = QComboBox(); self.refresh_ports()
        ef.addRow(self.T("serial"), self.port_combo); e.layout().addLayout(ef)
        er = QHBoxLayout(); er.addWidget(button(self.T("detect"), self.refresh_ports))
        self.install_button = button(self.T("flash"), self.flash_firmware, True)
        er.addWidget(self.install_button); er.addStretch()
        e.layout().addLayout(er); self.flash_progress = QProgressBar(); self.flash_progress.setValue(0)
        e.layout().addWidget(self.flash_progress)
        self.flash_status = self.label("", "subtitle")
        e.layout().addWidget(self.flash_status)
        e.layout().addWidget(self.label(self.T("tip"), "good")); lay.addWidget(e)
        pairing = card(); pairing.layout().addWidget(self.label(self.T("pairing_step"), "section"))
        self.setup_pairing_card = pairing
        self.setup_pairing_guide = self.label("", "supportCopy")
        pairing.layout().addWidget(self.setup_pairing_guide)
        tools = QHBoxLayout()
        self.setup_pair_button = button(self.T("pair"), self.pair_camera, True)
        tools.addWidget(self.setup_pair_button)
        tools.addWidget(button(self.T("shot"), self.test_shutter))
        self.setup_unpair_button = button(self.T("unpair"), self.unpair_camera)
        tools.addWidget(self.setup_unpair_button)
        tools.addWidget(button(self.T("open_dashboard"), self.open_esp_dashboard))
        tools.addStretch(); pairing.layout().addLayout(tools); lay.addWidget(pairing); lay.addStretch()
        self.update_camera_guides()
        self.p_host.textChanged.connect(self.update_setup_steps)
        self.ssid.currentTextChanged.connect(self.update_setup_steps)
        self.ssid.currentTextChanged.connect(self.invalidate_camera_step)
        self.password.textChanged.connect(self.update_setup_steps)
        self.password.textChanged.connect(self.invalidate_camera_step)
        self.port_combo.currentIndexChanged.connect(self.update_setup_steps)
        self.camera_target.currentIndexChanged.connect(self.update_setup_steps)
        self.update_setup_steps()
        return page

    def build_timelapse_page(self):
        page, lay = self.page_shell(self.T("time_title"))
        source = card(); source.layout().addWidget(self.label(self.T("source_section"),"section"))
        source_form = QFormLayout()
        self.photos = QLineEdit(); self.video = QLineEdit()
        pr = QHBoxLayout(); pr.addWidget(self.photos,1); pr.addWidget(button(self.T("choose"),self.choose_photos))
        vr = QHBoxLayout(); vr.addWidget(self.video,1); vr.addWidget(button(self.T("choose"),self.choose_video))
        self.sort_order=QComboBox(); self.sort_order.addItems([self.T("sort_name"),self.T("sort_date")])
        source_form.addRow(self.T("photos"),pr); source_form.addRow(self.T("sort_order"),self.sort_order)
        source.layout().addLayout(source_form); lay.addWidget(source)

        video_card=card(); video_card.layout().addWidget(self.label(self.T("video_section"),"section"))
        video_form=QFormLayout()
        self.fps = QSpinBox(); self.fps.setRange(1,60); self.fps.setValue(30)
        self.ratio = QComboBox()
        for title, dimensions in [
            (self.T("social_landscape"), (1920, 1080)),
            (self.T("social_vertical"), (1080, 1920)),
            (self.T("social_square"), (1080, 1080)),
            (self.T("social_portrait"), (1080, 1350)),
            (self.T("social_wide"), (1200, 628)),
            (self.T("social_classic"), (1440, 1080)),
            (self.T("social_classic_portrait"), (1080, 1440)),
            (self.T("social_pinterest"), (1000, 1500)),
            (self.T("social_original"), None),
        ]:
            self.ratio.addItem(title, dimensions)
        self.codec=QComboBox(); self.codec.addItems(["H.264 (compatible)","H.265 (smaller file)"])
        self.quality=QComboBox(); self.quality.addItems([self.T("quality_high"),self.T("quality_standard"),self.T("quality_small")])
        video_form.addRow(self.T("output"),vr); video_form.addRow(self.T("fps"),self.fps)
        video_form.addRow(self.T("ratio"),self.ratio); video_form.addRow(self.T("codec"),self.codec)
        video_form.addRow(self.T("quality"),self.quality)
        video_card.layout().addLayout(video_form); lay.addWidget(video_card)

        framing_card=card(); framing_card.layout().addWidget(self.label(self.T("framing_section"),"section"))
        framing_form=QFormLayout()
        self.framing = QComboBox(); self.framing.addItems([self.T("fit"),self.T("fill"),self.T("stretch")])
        self.position=QComboBox(); self.position.addItems([self.T("center"),self.T("top"),self.T("bottom"),self.T("left"),self.T("right")])
        self.rotation=QComboBox(); self.rotation.addItems(["0°","90°","180°","270°"])
        self.background=QComboBox(); self.background.addItems([self.T("black"),self.T("dark"),self.T("white")])
        framing_form.addRow(self.T("framing"),self.framing); framing_form.addRow(self.T("crop_position"),self.position)
        framing_form.addRow(self.T("rotation"),self.rotation); framing_form.addRow(self.T("background"),self.background)
        framing_card.layout().addLayout(framing_form)
        framing_card.layout().addWidget(self.label(self.T("preview"), "subtitle"))
        self.crop_preview = QLabel()
        self.crop_preview.setFixedSize(520, 300)
        self.crop_preview.setAlignment(Qt.AlignCenter)
        self.crop_preview.setStyleSheet(
            "background:#101218;border:1px solid #303541;border-radius:10px;")
        framing_card.layout().addWidget(self.crop_preview, 0, Qt.AlignHCenter)
        for control in (
                self.ratio, self.framing, self.position, self.rotation,
                self.background, self.sort_order):
            control.currentIndexChanged.connect(self.update_timelapse_preview)
        self.photos.textChanged.connect(self.update_timelapse_preview)
        lay.addWidget(framing_card)

        action=card(); action.layout().addWidget(button(self.T("render"), self.render_video, True))
        self.render_progress = QProgressBar(); action.layout().addWidget(self.render_progress); lay.addWidget(action); lay.addStretch()
        return page

    def build_esp_page(self):
        page, lay = self.page_shell(self.T("esp_page_title"))
        status = card()
        header = QHBoxLayout()
        header.addWidget(self.label(self.T("esp_connection"), "section")); header.addStretch()
        self.esp_selector = QComboBox()
        self.esp_selector.setMinimumWidth(260)
        self.esp_selector.setEditable(True)
        self.esp_selector.setInsertPolicy(QComboBox.NoInsert)
        self.esp_selector.addItem(
            self.esp_host.text().strip(), self.esp_host.text().strip())
        self.esp_selector.currentIndexChanged.connect(self.select_esp)
        self.esp_selector.lineEdit().editingFinished.connect(
            self.select_typed_esp)
        header.addWidget(self.esp_selector)
        header.addWidget(button(self.T("scan_esps"), self.scan_esps))
        header.addWidget(button(self.T("refresh"), self.refresh_esp_status, True))
        header.addWidget(button(self.T("open_dashboard"), self.open_esp_dashboard))
        status.layout().addLayout(header)
        self.esp_connection_message = self.label(self.T("esp_not_checked"), "subtitle")
        status.layout().addWidget(self.esp_connection_message)
        self.esp_metrics = {}
        metrics = QGridLayout()
        for index, (key, title) in enumerate([
            ("firmware", self.T("esp_firmware")), ("ip", self.T("esp_ip")),
            ("wifi", "Wi-Fi"), ("camera", self.T("camera_used")),
            ("bluetooth", "Bluetooth"),
            ("printer", self.T("esp_printer")), ("layer", self.T("layer")),
            ("delay", self.T("shutter_delay")),
        ]):
            widget = self.metric_widget(title, "—")
            metrics.addWidget(widget[0], index // 3, index % 3)
            self.esp_metrics[key] = widget[1]
        status.layout().addLayout(metrics)
        actions = QHBoxLayout()
        self.esp_pair_button = button(self.T("pair"), self.pair_camera, True)
        actions.addWidget(self.esp_pair_button)
        actions.addWidget(button(self.T("shot"), self.test_shutter))
        actions.addWidget(button(self.T("test_led"), self.test_led))
        self.esp_unpair_button = button(self.T("unpair"), self.unpair_camera)
        actions.addWidget(self.esp_unpair_button)
        actions.addStretch(); status.layout().addLayout(actions)
        lay.addWidget(status)
        guide = card(); guide.layout().addWidget(self.label(self.T("pairing_step"), "section"))
        self.esp_pairing_guide = self.label("", "supportCopy")
        guide.layout().addWidget(self.esp_pairing_guide)
        lay.addWidget(guide); lay.addStretch()
        self.update_camera_guides()
        return page

    def scan_esps(self):
        current = self.esp_host.text().strip()
        self.esp_connection_message.setText(self.T("scanning_esps"))
        self.run(
            discover_esps, ((current,),),
            self.esps_discovered,
            lambda error: self.esp_connection_message.setText(
                "✕ " + str(error)))

    def esps_discovered(self, devices):
        self.esp_selector.blockSignals(True)
        self.esp_selector.clear()
        if not devices:
            current = self.esp_host.text().strip()
            self.esp_selector.addItem(current, current)
            self.esp_connection_message.setText(self.T("no_esp_detected"))
        else:
            for status in devices:
                address = status["_resolved_address"]
                hostname = str(status.get("hostname") or "").strip()
                identity = hostname if hostname.endswith(".local") else address
                printer = status.get("printer") or self.T("no_printer")
                camera = status.get("camera_name") or status.get("camera_type", "")
                self.esp_selector.addItem(
                    f"{hostname or address} ({address}) — {printer} — {camera}",
                    identity)
            current_index = self.esp_selector.findData(
                self.esp_host.text().strip())
            self.esp_selector.setCurrentIndex(
                current_index if current_index >= 0 else 0)
            self.esp_connection_message.setText(
                self.T("esp_count").format(count=len(devices)))
        self.esp_selector.blockSignals(False)
        self.select_esp(self.esp_selector.currentIndex())

    def select_esp(self, index):
        if not hasattr(self, "esp_selector"):
            return
        address = self.esp_selector.itemData(index)
        if not address:
            return
        self.esp_host.setText(address)
        self.settings.setValue("esp_host", address)
        self.refresh_esp_status()

    def select_typed_esp(self):
        address = self.esp_selector.currentText().strip()
        if not address:
            return
        self.esp_host.setText(address)
        self.settings.setValue("esp_host", address)
        self.refresh_esp_status()

    def build_about_page(self):
        page, lay = self.page_shell(self.T("about")); c = card()
        c.layout().addWidget(self.label("Hackman3D LayerShot", "title"))
        c.layout().addWidget(self.label(f"{self.T('version')} {__version__}", "good"))
        c.layout().addWidget(self.label(self.T("support"))); c.layout().addWidget(self.label(self.T("about_text"), "section"))
        r = QHBoxLayout()
        for text,url in [("YouTube","https://youtube.com/@hackman3d"),("Instagram","https://www.instagram.com/hackman_3dprint/"),
                         ("TikTok","https://tiktok.com/@hackman3d"),("Creality Cloud","https://www.crealitycloud.com/user/5221417142"),
                         ("PayPal","https://paypal.me/hackman3d"),(self.T("feedback"),"mailto:hackman3d.pro@gmail.com")]:
            r.addWidget(button(text, lambda checked=False,u=url:self.open_url(u)))
        r.addStretch(); c.layout().addLayout(r); lay.addWidget(c); lay.addStretch(); return page

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav_buttons): b.setChecked(i == index)
        if index == 1 and hasattr(self, "setup_progress"):
            self.update_setup_steps()
        if index == 2 and hasattr(self, "esp_metrics"):
            QTimer.singleShot(0, self.refresh_esp_status)

    def set_setup_card_unlocked(self, card, unlocked):
        card.setEnabled(unlocked)
        card.setVisible(unlocked)
        card.setProperty("locked", not unlocked)
        card.style().unpolish(card)
        card.style().polish(card)

    def update_setup_steps(self, *_):
        if not hasattr(self, "setup_pairing_card"):
            return
        printer_ready = bool(self.printers)
        wifi_ready = (
            printer_ready and bool(self.ssid.currentText().strip())
            and bool(self.password.text()))
        camera_ready = (
            wifi_ready and self.camera_target.currentData() is not None
            and self.camera_step_confirmed)
        port_ready = camera_ready and bool(self.port_combo.currentText())
        pairing_ready = self.firmware_ready and camera_ready
        self.set_setup_card_unlocked(self.setup_printer_card, True)
        self.set_setup_card_unlocked(self.setup_wifi_card, printer_ready)
        self.set_setup_card_unlocked(self.setup_camera_card, wifi_ready)
        self.set_setup_card_unlocked(self.setup_flash_card, camera_ready)
        self.set_setup_card_unlocked(
            self.setup_pairing_card, pairing_ready)
        if hasattr(self, "install_button"):
            self.install_button.setEnabled(
                port_ready and not getattr(self, "_flash_in_progress", False))
        if not printer_ready:
            message = self.T("guide_printer")
        elif not wifi_ready:
            message = self.T("guide_wifi")
        elif not camera_ready:
            message = self.T("guide_camera")
        elif pairing_ready:
            message = self.T("guide_pair")
        elif not port_ready:
            message = self.T("guide_usb")
        else:
            message = self.T("guide_install")
        self.setup_progress.setText(message)

    def detect_existing_esp(self):
        if self.firmware_ready:
            return
        self.run(
            esp_status, (self.esp_host.text().strip(),),
            self.existing_esp_found, lambda _error: None)

    def existing_esp_found(self, _status):
        self.firmware_ready = True
        self.settings.setValue("firmware_installed", True)
        self.update_setup_steps()

    def change_language(self):
        code = self.language.currentData()
        if code == self.lang: return
        self.settings.setValue("language", code)
        QMessageBox.information(self, "LayerShot", "The new language will be applied after restarting the app.")

    def camera_target_changed(self):
        self.camera_target_value = self.camera_target.currentData() or "iphone"
        self.settings.setValue("camera_target", self.camera_target_value)
        self.camera_step_confirmed = False
        self.update_camera_guides()
        self.update_setup_steps()

    def invalidate_camera_step(self, *_):
        self.camera_step_confirmed = False
        self.update_setup_steps()

    def shutter_delay_changed(self, *_):
        delay = self.shutter_delay.currentData()
        self.settings.setValue("shutter_delay_ms", delay)
        self.invalidate_camera_step()
        # Once an ESP is installed, apply timer changes immediately. A full
        # reflash is only needed when selecting a different camera firmware.
        if self.firmware_ready and self.esp_host.text().strip():
            self.run(
                esp_post,
                (self.esp_host.text().strip(), "delay", {"delay": delay}),
                lambda _result: self.refresh_esp_status(),
                lambda _error: None)

    def confirm_camera_step(self):
        self.camera_step_confirmed = True
        self.settings.setValue(
            "shutter_delay_ms", self.shutter_delay.currentData())
        self.update_setup_steps()

    def camera_target_name(self, target=None):
        target = target or self.camera_target_value
        key = {
            "iphone": "camera_iphone",
            "android": "camera_android",
            "hid_volume_up": "camera_hid_volume_up",
            "hid_volume_down": "camera_hid_volume_down",
            "hid_enter": "camera_hid_enter",
            "hid_space": "camera_hid_space",
            "dji": "camera_dji",
            "gopro": "camera_gopro",
            "insta360": "camera_insta360",
        }.get(target, "camera_iphone")
        return self.T(key)

    def camera_pairing_guide(self, target=None):
        target = target or self.camera_target_value
        return self.T({
            "iphone": "pairing_guide_iphone",
            "android": "pairing_guide_android",
            "hid_volume_up": "pairing_guide_hid",
            "hid_volume_down": "pairing_guide_hid",
            "hid_enter": "pairing_guide_hid",
            "hid_space": "pairing_guide_hid",
            "dji": "pairing_guide_dji",
            "gopro": "pairing_guide_gopro",
            "insta360": "pairing_guide_insta360",
        }.get(target, "pairing_guide_iphone"))

    def camera_compatibility_text(self, target=None):
        target = target or self.camera_target_value
        return self.T({
            "iphone": "compatibility_iphone",
            "android": "compatibility_android",
            "hid_volume_up": "compatibility_hid_volume_up",
            "hid_volume_down": "compatibility_hid_volume_down",
            "hid_enter": "compatibility_hid_enter",
            "hid_space": "compatibility_hid_space",
            "dji": "compatibility_dji",
            "gopro": "compatibility_gopro",
            "insta360": "compatibility_insta360",
        }.get(target, "compatibility_iphone"))

    def update_camera_guides(self):
        guide = self.camera_pairing_guide()
        if hasattr(self, "camera_compatibility"):
            self.camera_compatibility.setText(self.camera_compatibility_text())
        for attribute in ("install_pairing_guide", "setup_pairing_guide",
                          "esp_pairing_guide"):
            widget = getattr(self, attribute, None)
            if widget is not None:
                widget.setText(guide)
        pair_text = self.T({
            "dji": "pair_dji",
            "gopro": "pair_gopro",
            "insta360": "pair_insta360",
        }.get(self.camera_target_value, "pair"))
        for attribute in ("setup_pair_button", "esp_pair_button"):
            widget = getattr(self, attribute, None)
            if widget is not None:
                widget.setText(pair_text)

    def run(self, fn, args=(), done=None, failed=None):
        worker = Worker(fn,*args)
        self.active_workers.add(worker)
        def completed(result):
            self.active_workers.discard(worker)
            if not self.closing and done: done(result)
        def rejected(error):
            self.active_workers.discard(worker)
            if self.closing:
                return
            handler = failed or (lambda message: QMessageBox.warning(self,"LayerShot",message))
            handler(error)
        worker.signals.done.connect(completed)
        worker.signals.failed.connect(rejected)
        self.pool.start(worker)

    def check_for_updates(self):
        def show_if_newer(release):
            tag = str(release.get("tag_name", "")).lstrip("vV")
            def version_tuple(value):
                return tuple(
                    int(part) for part in value.split(".")
                    if part.isdigit())
            if not tag or version_tuple(tag) <= version_tuple(__version__):
                return
            url = release.get("html_url")
            if not url:
                return
            self.update_message.setText(
                self.T("update_available").format(version=tag))
            try:
                self.update_button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.update_button.clicked.connect(
                lambda checked=False, address=url: self.open_url(address))
            self.update_banner.show()
        self.run(
            latest_layershot_release,
            done=show_if_newer,
            failed=lambda _error: None)

    def closeEvent(self, event):
        self.closing = True
        if hasattr(self, "poller"):
            self.poller.stop()
        event.accept()

    def save_printer(self):
        host = self.p_host.text().strip()
        if not host: return
        item={"id":host+":"+str(self.p_port.value()),"name":self.p_name.text().strip() or self.p_model.currentText(),
              "model":self.p_model.currentText(),"host":host,"port":self.p_port.value()}
        self.printers=[p for p in self.printers if p["id"] != item["id"]]+[item]
        self.active_printer_id = item["id"]
        self.settings.setValue("active_printer_id", item["id"])
        self.settings.setValue("printers",json.dumps(self.printers))
        self._refresh_printer_cards()
        self.update_setup_steps()
        self.refresh_all()

    def test_printer(self):
        self.test_result.setText(self.T("connecting"))
        self.run(printer_status,(self.p_host.text().strip(),self.p_port.value()),
                 self.printer_test_succeeded,
                 lambda e:self.test_result.setText("✕ "+e))

    def scan_printers(self):
        self.discovery_button.setEnabled(False)
        self.discovered_printers.clear()
        self.discovered_printers.addItem(self.T("scanning_network"), None)
        self.test_result.setText(self.T("scanning_network"))
        seeds = list(self.printers)
        typed_host = self.p_host.text().strip()
        if typed_host:
            seeds.append({"host": typed_host})
        self.run(
            discover_printers, (tuple(seeds),),
            self.printers_discovered, self.printer_scan_failed)

    def printers_discovered(self, printers):
        self.discovery_button.setEnabled(True)
        self.discovered_printers.blockSignals(True)
        self.discovered_printers.clear()
        if not printers:
            self.discovered_printers.addItem(self.T("no_discovered_printer"), None)
            self.test_result.setText(self.T("no_discovered_printer"))
        else:
            self.discovered_printers.addItem(
                self.T("discovered_count").format(count=len(printers)), None)
            for printer in printers:
                label = (f"{printer['name']} — {printer['model']} — "
                         f"{printer['host']}:{printer['port']}")
                self.discovered_printers.addItem(label, printer)
            self.test_result.setText(self.T("select_discovered_printer"))
        self.discovered_printers.blockSignals(False)

    def printer_scan_failed(self, error):
        self.discovery_button.setEnabled(True)
        self.discovered_printers.clear()
        self.discovered_printers.addItem(self.T("no_discovered_printer"), None)
        self.test_result.setText("✕ " + error)

    def select_discovered_printer(self, index):
        printer = self.discovered_printers.itemData(index)
        if not printer:
            return
        self.p_host.setText(printer["host"])
        self.p_port.setValue(printer["port"])
        self.p_name.setText(printer["name"])
        model_index = self.p_model.findText(printer["model"])
        self.p_model.setCurrentIndex(
            model_index if model_index >= 0 else self.p_model.count() - 1)
        self.active_printer_id = (
            printer["host"] + ":" + str(printer["port"]))
        self.settings.setValue(
            "active_printer_id", self.active_printer_id)
        self.test_result.setText(
            f"✓ Moonraker — {printer['host']}:{printer['port']}")

    def active_printer(self):
        for printer in self.printers:
            if printer.get("id") == self.active_printer_id:
                return printer
        return self.printers[0] if self.printers else None

    def esp_hostname_for_printer(self, printer):
        slug = re.sub(
            r"[^a-z0-9]+", "",
            str(printer.get("name") or printer.get("model") or "").lower())
        return ("hackman-layershot-" + (slug or "printer"))[:63]

    def printer_test_succeeded(self, data):
        actual_port = data[2]
        self.p_port.setValue(actual_port)
        self.test_result.setText(
            f"✓ {self.T('online')} — Moonraker {self.p_host.text().strip()}:{actual_port}")

    def _refresh_printer_cards(self):
        while self.printer_grid.count():
            w=self.printer_grid.takeAt(0).widget()
            if w: w.deleteLater()
        self.cards={}
        self.camera_views={}
        if not self.printers:
            self.printer_grid.addWidget(self.label(self.T("no_printer"),"subtitle"),0,0); return
        for i,p in enumerate(self.printers):
            c=card()
            header=QHBoxLayout(); header.addWidget(self.label(p["name"],"printerName")); header.addStretch()
            remove=button(self.T("remove"),lambda checked=False,x=p:self.remove_printer(x["id"]))
            remove.setObjectName("danger"); header.addWidget(remove); c.layout().addLayout(header)
            c.layout().addWidget(self.label(f"{p['model']} · {p['host']}:{p['port']}","printerMeta"))
            filename=self.label("—","filename"); c.layout().addWidget(filename)
            metrics=QHBoxLayout()
            state=self.metric_widget(self.T("status"),self.T("offline"))
            layer=self.metric_widget(self.T("layer"),"—")
            progress=self.metric_widget(self.T("progress"),"—")
            metrics.addWidget(state[0]); metrics.addWidget(layer[0]); metrics.addWidget(progress[0])
            c.layout().addLayout(metrics)
            bar=QProgressBar(); c.layout().addWidget(bar)
            camera_host=QWidget(); camera_layout=QVBoxLayout(camera_host)
            camera_layout.setContentsMargins(0,0,0,0)
            camera_view = CameraView(p["host"], p["port"])
            camera_layout.addWidget(camera_view)
            c.layout().addWidget(camera_host)
            camera_button=button(self.T("camera_show"),lambda checked=False,x=p:self.toggle_camera(x["id"]))
            camera_button.setCheckable(True)
            camera_button.setChecked(True)
            camera_button.setText(self.T("camera_hide"))
            c.layout().addWidget(camera_button,0,Qt.AlignLeft)
            self.printer_grid.addWidget(c,i//2,i%2)
            self.cards[p["id"]]=(state[1],layer[1],progress[1],filename,bar)
            self.camera_views[p["id"]]={"host":camera_host,"layout":camera_layout,
                                        "button":camera_button,"view":camera_view,"printer":p}

    def metric_widget(self, title, value):
        frame=QFrame(); frame.setObjectName("metric"); layout=QVBoxLayout(frame)
        layout.setContentsMargins(12,10,12,10); layout.setSpacing(3)
        layout.addWidget(self.label(title,"metricLabel"))
        value_label=self.label(value,"metricValue"); layout.addWidget(value_label)
        return frame,value_label

    def toggle_camera(self, printer_id):
        if printer_id not in self.camera_views: return
        item=self.camera_views[printer_id]; visible=not item["host"].isVisible()
        if visible and item["view"] is None:
            printer=item["printer"]
            view=CameraView(printer["host"], printer["port"])
            item["layout"].addWidget(view); item["view"]=view
        item["host"].setVisible(visible)
        item["button"].setText(self.T("camera_hide") if visible else self.T("camera_show"))

    def refresh_all(self):
        for p in self.printers:
            self.run(printer_status,(p["host"],p["port"]),lambda data,x=p:self.update_card(x,data),
                     lambda error,x=p:self.fail_card(x,error))

    def refresh_esp_status(self):
        if not hasattr(self, "esp_metrics") or self.stack.currentIndex() != 2:
            return
        self.esp_connection_message.setText(self.T("connecting"))
        self.run(esp_status, (self.esp_host.text().strip(),),
                 self.update_esp_status, self.fail_esp_status)

    def update_esp_status(self, status):
        self.firmware_ready = True
        self.settings.setValue("firmware_installed", True)
        self.update_setup_steps()
        # Keep the stable Bonjour hostname as the saved identity. The numeric
        # DHCP address is displayed below but must not replace the hostname,
        # otherwise the app becomes stuck when the router leases a new IP.
        hostname = str(status.get("hostname") or "").strip()
        identity = (
            hostname if hostname.endswith(".local")
            else self.esp_host.text().strip())
        if identity:
            self.esp_host.setText(identity)
            self.settings.setValue("esp_host", identity)
        self.esp_connection_message.setText(
            "✓ " + self.T("esp_connected") + " — " + status.get("hostname", "hackman-layershot.local"))
        self.esp_metrics["firmware"].setText(str(status.get("firmware", "—")))
        self.esp_metrics["ip"].setText(str(status.get("ip", "—")))
        self.esp_metrics["wifi"].setText(self.T("online") if status.get("wifi") else self.T("offline"))
        target = status.get("camera_type") or self.camera_target_value
        self.camera_target_value = target
        self.settings.setValue("camera_target", target)
        if hasattr(self, "camera_target"):
            index = self.camera_target.findData(target)
            if index >= 0 and index != self.camera_target.currentIndex():
                self.camera_target.blockSignals(True)
                self.camera_target.setCurrentIndex(index)
                self.camera_target.blockSignals(False)
        self.update_camera_guides()
        self.esp_metrics["camera"].setText(
            status.get("camera_name") or self.camera_target_name(target))
        self.esp_metrics["bluetooth"].setText(
            self.T("esp_camera_connected") if status.get("bluetooth")
            else (self.T("esp_detectable") if status.get("pairing") else self.T("offline")))
        printer = status.get("printer") or "—"
        self.esp_metrics["printer"].setText(
            printer if status.get("printer_connected") else printer + " · " + self.T("offline"))
        current, total = status.get("current_layer", -1), status.get("total_layers", -1)
        self.esp_metrics["layer"].setText(
            f"{current} / {total}" if current is not None and current >= 0 and total and total > 0
            else (str(current) if current is not None and current >= 0 else "—"))
        delay_ms = status.get("shutter_delay_ms")
        self.esp_metrics["delay"].setText(
            f"{delay_ms / 1000:g} s"
            if isinstance(delay_ms, (int, float)) and delay_ms >= 0 else "—")

    def fail_esp_status(self, error):
        address = self.esp_host.text().strip() or "hackman-layershot.local"
        self.esp_connection_message.setText(
            "✕ " + self.T("esp_unreachable") + " — " + address)
        for label in self.esp_metrics.values():
            label.setText("—")

    def update_card(self,p,data):
        if p["id"] not in self.cards:return
        stats,display,actual_port=data
        state,layer,progress_label,filename_label,bar=self.cards[p["id"]]
        filename=stats.get("filename") or "—"; status=stats.get("state") or "ready"; progress=int(float(display.get("progress",0))*100)
        if status == "preparing":
            status = self.T("preparing")
        info=stats.get("info") or {}; current=info.get("current_layer"); total=info.get("total_layer")
        state.setText(status); layer.setText(f"{current} / {total}" if current is not None and total else "—")
        progress_label.setText(f"{progress} %"); filename_label.setText(filename); bar.setValue(progress)

    def fail_card(self,p,error):
        if p["id"] in self.cards:
            state,layer,progress,filename,bar=self.cards[p["id"]]
            state.setText(self.T("offline")); layer.setText("—"); progress.setText("—")
            filename.setText(error); bar.setValue(0)

    def remove_printer(self,pid):
        self.printers=[p for p in self.printers if p["id"]!=pid]; self.settings.setValue("printers",json.dumps(self.printers)); self._refresh_printer_cards()
        if pid == self.active_printer_id:
            self.active_printer_id = (
                self.printers[0]["id"] if self.printers else "")
            self.settings.setValue(
                "active_printer_id", self.active_printer_id)
        if hasattr(self, "setup_progress"):
            self.update_setup_steps()
    def refresh_ports(self):
        if not hasattr(self,"port_combo"): return
        current=self.port_combo.currentText(); self.port_combo.clear(); self.port_combo.addItems(serial_ports())
        if current:self.port_combo.setCurrentText(current)
        if hasattr(self, "install_button"):
            self.update_setup_steps()
    def fill_known_password(self,ssid):
        if ssid and not self.password.text(): self.password.setText(known_wifi_password(ssid))

    def load_known_wifi_password(self):
        password = known_wifi_password(self.ssid.currentText().strip())
        if password:
            self.password.setText(password)
        else:
            QMessageBox.information(
                self, "LayerShot", self.T("saved_password_not_found"))

    def toggle_wifi_password(self, checked=False):
        self.password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.password_visibility.setToolTip(
            self.T("hide_password") if checked else self.T("show_password"))

    def flash_firmware(self):
        if getattr(self, "_flash_in_progress", False):
            return
        port=self.port_combo.currentText()
        ssid=self.ssid.currentText().strip()
        wifi_password=self.password.text()
        camera_target = self.camera_target.currentData() or "iphone"
        shutter_delay_ms = self.shutter_delay.currentData()
        selected_printer = self.active_printer()
        esp_hostname = (
            self.esp_hostname_for_printer(selected_printer)
            if selected_printer else "hackman-layershot")
        firmware_name = {
            "dji": "Hackman3DLayerShotDJI.bin",
            "gopro": "Hackman3DLayerShotGoPro.bin",
            "insta360": "Hackman3DLayerShotInsta360.bin",
        }.get(camera_target, "Hackman3DLayerShotPhone.bin")
        fw=asset_path(firmware_name)
        missing = []
        if selected_printer is None:
            missing.append(self.T("missing_printer"))
        elif not selected_printer.get("host") or not selected_printer.get("port"):
            missing.append(self.T("missing_printer_address"))
        if not ssid:
            missing.append(self.T("missing_wifi"))
        normalized_ssid = ssid.lower().replace(" ", "").replace("-", "")
        if any(marker in normalized_ssid for marker in ("5ghz", "5gonly")) or normalized_ssid.endswith("5g"):
            missing.append(self.T("wifi_5ghz_unsupported"))
        if not wifi_password:
            missing.append(self.T("missing_wifi_password"))
        if not port:
            missing.append(self.T("missing_esp_port"))
        if not fw.exists():
            missing.append(self.T("missing_firmware"))
        if missing:
            QMessageBox.warning(
                self, "LayerShot",
                self.T("installation_incomplete") + "\n\n• " + "\n• ".join(missing))
            return
        self._flash_in_progress = True
        self.install_button.setEnabled(False)
        self.flash_progress.setRange(0,0)
        self.flash_status.setText(self.T("flash") + "…")
        printer=selected_printer
        def task():
            # Do not touch the ESP until the selected printer has answered.
            printer_status(printer["host"], printer["port"])
            import serial
            esptool_executable = asset_path("esptool.exe")
            esptool_arguments = [
                "--chip", "esp32c3", "--port", port,
                "--baud", "460800",
                "--before", "default-reset", "--after", "hard-reset",
                "write-flash", "0x0", str(fw),
            ]
            if (platform.system() == "Windows" and esptool_executable.exists()
                    and sys.maxsize > 2**32):
                windows_esptool_arguments = list(esptool_arguments)
                windows_esptool_arguments.insert(
                    windows_esptool_arguments.index("write-flash"),
                    "--no-stub")
                result = subprocess.run(
                    [str(esptool_executable), *windows_esptool_arguments],
                    check=False, capture_output=True, text=True,
                    **hidden_subprocess_kwargs())
                if result.returncode:
                    detail = (result.stderr or result.stdout or "").strip()
                    raise RuntimeError(
                        "ESP32 flashing failed on "
                        f"{port} (exit code {result.returncode}).\n\n"
                        + (detail or
                           "Hold BOOT, click Install and configure, then "
                           "release BOOT when the flash begins."))
            elif platform.system() == "Darwin":
                # Run esptool inside the existing LayerShot process. Launching
                # any bundled helper executable on macOS can make LaunchServices
                # create a second, empty application window.
                mac_esptool_arguments = list(esptool_arguments)
                mac_esptool_arguments.insert(
                    mac_esptool_arguments.index("write-flash"), "--no-stub")
                import esptool
                last_error = ""
                for attempt in range(8):
                    try:
                        esptool.main(mac_esptool_arguments)
                        break
                    except SystemExit as exc:
                        # Click/esptool reports a successful command with
                        # SystemExit(0). Continue with USB provisioning instead
                        # of silently terminating the QRunnable.
                        if exc.code in (None, 0):
                            break
                        raise RuntimeError(
                            f"ESP32 flashing stopped with exit code {exc.code}.") from exc
                    except Exception as exc:
                        last_error = str(exc)
                        port_busy = any(marker in last_error.lower() for marker in (
                            "resource temporarily unavailable",
                            "could not exclusively lock port",
                            "port is busy",
                        ))
                        if not port_busy:
                            raise
                        # A previous attempt or the USB refresh can hold the
                        # device briefly. Let macOS release it and retry.
                        time.sleep(1.25)
                else:
                    raise RuntimeError(
                        "The ESP32 USB port is still busy. Close Arduino IDE, "
                        "Serial Monitor and any other LayerShot window, unplug "
                        "and reconnect the ESP32, then try again.\n\n" +
                        last_error)
            else:
                import esptool
                esptool.main(esptool_arguments)
            command="\t".join([
                "LAYERSHOT_CONFIG",
                ssid.encode().hex(),
                wifi_password.encode().hex(),
                printer["host"], str(printer["port"]),
                "1", "0", "0", str(shutter_delay_ms),
                camera_target,
                esp_hostname,
            ])+"\n"
            # Windows can take several seconds to release esptool's handle and
            # enumerate the ESP32-C3 USB CDC port again after the hard reset.
            time.sleep(2 if platform.system() == "Windows" else .5)
            deadline=time.monotonic()+(50 if platform.system() == "Windows" else 25)
            last_error=""
            attempted_ports=set()
            while time.monotonic()<deadline:
                for current_port in dict.fromkeys((port, *serial_ports())):
                    attempted_ports.add(current_port)
                    try:
                        # Configure the control lines before opening the port.
                        # Opening a Windows COM port with pyserial's default
                        # DTR/RTS state can reset the C3 and prevent it from
                        # ever receiving the provisioning command.
                        connection = serial.Serial(
                            port=None, baudrate=115200, timeout=.25,
                            write_timeout=2)
                        connection.dtr = False
                        connection.rts = False
                        connection.port = current_port
                        connection.open()
                        try:
                            time.sleep(1.5)
                            connection.reset_input_buffer()
                            # Terminate any partial boot/provisioning line left
                            # in the ESP receive buffer before sending the real
                            # configuration. This is needed by both Arduino and
                            # ESP-IDF firmware after a USB reset.
                            connection.write(b"\n")
                            connection.flush()
                            time.sleep(.2)
                            opened_until=min(deadline,time.monotonic()+12)
                            answer=bytearray()
                            next_send=0
                            while time.monotonic()<opened_until:
                                if time.monotonic()>=next_send:
                                    connection.write(command.encode())
                                    connection.flush()
                                    next_send=time.monotonic()+1
                                answer.extend(connection.read(512))
                                if b"LAYERSHOT_CONFIG_OK" in answer:
                                    save_wifi_password(ssid, wifi_password)
                                    return True
                                if b"LAYERSHOT_CONFIG_ERROR" in answer:
                                    last_error = (
                                        "The ESP32 rejected the Wi-Fi configuration. "
                                        "The app is retrying with a clean USB line.")
                                    answer.clear()
                                    connection.write(b"\n")
                                    connection.flush()
                                    next_send=time.monotonic()+.25
                            last_error=bytes(answer).decode(errors="replace").strip()
                        finally:
                            connection.close()
                    except Exception as exc:
                        last_error=str(exc)
                        if (platform.system() == "Windows" and
                                ("access is denied" in last_error.lower() or
                                 "permissionerror" in last_error.lower() or
                                 "permission error" in last_error.lower())):
                            last_error = (
                                f"{current_port} is already in use. Close "
                                "Arduino IDE, Serial Monitor, Creality Print "
                                "and every other LayerShot window, then unplug "
                                "and reconnect the ESP32.")
                time.sleep(0.8)
            port_list=", ".join(sorted(attempted_ports)) or "none"
            raise ConnectionError(
                "The firmware was installed, but the USB configuration was "
                f"not acknowledged. COM ports tried: {port_list}. {last_error}")
        def finish_flash():
            self._flash_in_progress = False
            self.flash_progress.setRange(0,100)
            self.update_setup_steps()
        def flash_done(_):
            finish_flash()
            self.firmware_ready = True
            self.settings.setValue("firmware_installed", True)
            self.esp_host.setText(esp_hostname + ".local")
            self.settings.setValue("esp_host", esp_hostname + ".local")
            self.update_setup_steps()
            self.flash_progress.setValue(100)
            self.flash_status.setObjectName("good")
            self.flash_status.setText(
                "Firmware and settings installed. The ESP32 is connecting to Wi-Fi.")
            self.flash_status.style().unpolish(self.flash_status)
            self.flash_status.style().polish(self.flash_status)
        def flash_failed(error):
            finish_flash()
            self.flash_status.setObjectName("error")
            self.flash_status.setText(error)
            self.flash_status.style().unpolish(self.flash_status)
            self.flash_status.style().polish(self.flash_status)
        self.run(task, done=flash_done, failed=flash_failed)

    def configure_esp(self):
        host=self.esp_host.text().strip().removeprefix("http://").rstrip("/")
        def task():
            errors=[]
            for candidate in dict.fromkeys((host, "192.168.4.1")):
                try:
                    printer = self.active_printer()
                    if printer:
                        esp_post(candidate,"printer-config",{"host":printer["host"],"port":printer["port"],
                                 "every":1,"skip":0,"stop":0,
                                 "delay":self.shutter_delay.currentData()})
                    esp_post(candidate,"configure",{"ssid":self.ssid.currentText(),"password":self.password.text()})
                    return candidate
                except Exception as exc:
                    errors.append(str(exc))
            raise ConnectionError(
                "LayerShot ESP32 was not found. Connect the Mac to the "
                "“Hackman3D-LayerShot-Setup” Wi-Fi network, then send the settings again.")
        self.run(task,done=lambda _:QMessageBox.information(
            self,"LayerShot","Settings stored in the ESP32. It is restarting now."))
    def pair_camera(self):
        target = self.camera_target_value
        message = self.T({
            "dji": "pairing_started_dji",
            "gopro": "pairing_started_gopro",
            "insta360": "pairing_started_insta360",
        }.get(target, "pairing_started_phone"))
        self.run(
            esp_post, (self.esp_host.text().strip(), "pair", {}),
            lambda _: QMessageBox.information(self, "LayerShot", message))

    def unpair_camera(self):
        self.run(
            esp_post, (self.esp_host.text().strip(), "reset-bonds", {}),
            lambda _: QMessageBox.information(
                self, "LayerShot", self.T("pairing_deleted")))
    def open_esp_dashboard(self):
        host = self.esp_host.text().strip()
        if host in ("hackman-layershot.lan", "hackman-layershot-001.lan"):
            host = "hackman-layershot.local"
        # Opening the dashboard does not need another complete LAN discovery.
        # refresh_esp_status already stores the latest working numeric address,
        # so let the browser open it immediately. If only the mDNS name is
        # known, the browser resolves it itself.
        self.open_url(host if "://" in host else "http://" + host)
    def test_led(self):
        self.run(esp_post,(self.esp_host.text().strip(),"led-test",{}),lambda _:QMessageBox.information(self,"LayerShot","LED test completed."))
    def test_shutter(self): self.run(esp_post,(self.esp_host.text().strip(),"trigger",{}),lambda _:QMessageBox.information(self,"LayerShot","Shutter command sent."))
    def choose_photos(self):
        folder = QFileDialog.getExistingDirectory(self, self.T("photos"))
        if not folder:
            return
        self.photos.setText(folder)
        # Provide an immediately usable default while keeping the line edit
        # fully editable and the adjacent file chooser available.
        self.video.setText(str(Path(folder) / "LayerShot-timelapse.mp4"))
    def choose_video(self):
        f,_=QFileDialog.getSaveFileName(self,self.T("output"),"layershot-timelapse.mp4","MP4 video (*.mp4)")
        if f:self.video.setText(f)

    def update_timelapse_preview(self, *_):
        if not hasattr(self, "crop_preview"):
            return
        folder = Path(self.photos.text())
        if not folder.is_dir():
            self.crop_preview.clear()
            return
        images = [
            path for path in folder.iterdir()
            if path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES]
        images = sorted(
            images,
            key=(lambda path: path.stat().st_mtime)
            if self.sort_order.currentIndex()
            else (lambda path: path.name.lower()))
        if not images:
            self.crop_preview.setText("No compatible photo")
            return
        # Match FFmpeg's default behavior for phone photos: first apply the
        # EXIF orientation, then apply the rotation selected in LayerShot.
        # QPixmap(path) ignores that metadata on some Qt/macOS combinations,
        # which previously made the preview disagree with the final video.
        reader = QImageReader(str(images[0]))
        reader.setAutoTransform(True)
        source = QPixmap.fromImage(reader.read())
        if source.isNull():
            ffmpeg = self.find_ffmpeg()
            preview_file = Path("/private/tmp") / "layershot-format-preview.jpg"
            if ffmpeg:
                subprocess.run(
                    [ffmpeg, "-y", "-v", "error", "-i", str(images[0]),
                     "-frames:v", "1", str(preview_file)],
                    check=False, capture_output=True,
                    **hidden_subprocess_kwargs())
                source = QPixmap(str(preview_file))
        if source.isNull():
            self.crop_preview.setText("Preview unavailable")
            return
        rotation = self.rotation.currentIndex()
        if rotation:
            source = source.transformed(
                QTransform().rotate((90, 180, 270)[rotation - 1]),
                Qt.SmoothTransformation)
        dimensions = self.ratio.currentData()
        if dimensions:
            output_width, output_height = dimensions
        else:
            output_width, output_height = source.width(), source.height()
        scale = min(500 / output_width, 280 / output_height)
        width = max(1, round(output_width * scale))
        height = max(1, round(output_height * scale))
        mode = self.framing.currentIndex()
        if mode == 0:
            colors = ["black", "#151820", "white"]
            canvas = QPixmap(width, height)
            canvas.fill(QColor(colors[self.background.currentIndex()]))
            fitted = source.scaled(
                width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter = QPainter(canvas)
            painter.drawPixmap(
                (width - fitted.width()) // 2,
                (height - fitted.height()) // 2,
                fitted)
            painter.end()
        elif mode == 1:
            expanded = source.scaled(
                width, height, Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation)
            offsets = [
                ((expanded.width() - width) // 2,
                 (expanded.height() - height) // 2),
                ((expanded.width() - width) // 2, 0),
                ((expanded.width() - width) // 2,
                 expanded.height() - height),
                (0, (expanded.height() - height) // 2),
                (expanded.width() - width,
                 (expanded.height() - height) // 2),
            ]
            x, y = offsets[self.position.currentIndex()]
            canvas = expanded.copy(max(0, x), max(0, y), width, height)
        else:
            canvas = source.scaled(
                width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.crop_preview.setPixmap(canvas)

    def render_video(self):
        ffmpeg = self.find_ffmpeg()
        photos=Path(self.photos.text()); output=self.video.text().strip()
        if not photos.is_dir():
            QMessageBox.warning(
                self, "LayerShot",
                "Select a valid photo folder."); return
        if not output:
            QMessageBox.warning(
                self, "LayerShot",
                "Select where the MP4 video should be saved."); return
        if not ffmpeg:
            QMessageBox.warning(
                self, "LayerShot",
                "FFmpeg was not found. Reinstall LayerShot or install FFmpeg "
                "on this computer."); return
        images=[p for p in photos.iterdir()
                if p.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES]
        images=sorted(images,key=(lambda p:p.stat().st_mtime) if self.sort_order.currentIndex() else (lambda p:p.name.lower()))
        if not images: QMessageBox.warning(self,"LayerShot","No compatible photos found."); return
        manifest=photos/".layershot-input.txt"; manifest.write_text("".join(f"file '{str(p).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in images))
        self.render_progress.setRange(0,0)
        dimensions=self.ratio.currentData()
        filters=[]
        rotation=self.rotation.currentIndex()
        if rotation==1: filters.append("transpose=1")
        elif rotation==2: filters.extend(["hflip","vflip"])
        elif rotation==3: filters.append("transpose=2")
        if dimensions:
            width,height=dimensions; mode=self.framing.currentIndex()
            if mode==0:
                colors=["black","#151820","white"]; color=colors[self.background.currentIndex()]
                filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
                filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={color}")
            elif mode==1:
                positions=[("(iw-ow)/2","(ih-oh)/2"),("(iw-ow)/2","0"),("(iw-ow)/2","ih-oh"),("0","(ih-oh)/2"),("iw-ow","(ih-oh)/2")]
                x,y=positions[self.position.currentIndex()]
                filters.append(f"scale={width}:{height}:force_original_aspect_ratio=increase")
                filters.append(f"crop={width}:{height}:{x}:{y}")
            else:
                filters.append(f"scale={width}:{height}")
        codec=["libx264","libx265"][self.codec.currentIndex()]
        crf=[18,23,28][self.quality.currentIndex()]
        def task():
            command=[
                ffmpeg, "-y", "-r", str(self.fps.value()),
                "-f", "concat", "-safe", "0", "-i", str(manifest)]
            if filters: command.extend(["-vf",",".join(filters)])
            command.extend(["-c:v",codec,"-crf",str(crf),"-pix_fmt","yuv420p",output])
            subprocess.run(
                command, check=True, capture_output=True,
                **hidden_subprocess_kwargs())
            manifest.unlink(missing_ok=True); return True
        self.run(task,done=lambda _:(self.render_progress.setRange(0,100),self.render_progress.setValue(100),QMessageBox.information(self,"LayerShot","Timelapse created.")),
                 failed=lambda e:(self.render_progress.setRange(0,100),QMessageBox.warning(self,"LayerShot",e)))

    @staticmethod
    def find_ffmpeg():
        ffmpeg = None
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            candidate = Path(get_ffmpeg_exe())
            if candidate.is_file():
                ffmpeg = str(candidate)
        except Exception:
            pass
        if not ffmpeg:
            candidates = [
                shutil.which("ffmpeg"),
                str(Path.home() / ".local" / "bin" / "ffmpeg"),
                "/opt/homebrew/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
            ]
            ffmpeg = next(
                (candidate for candidate in candidates
                 if candidate and Path(candidate).is_file()),
                None)
        return ffmpeg
