import json, os, shutil, subprocess
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, QTimer, Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget
)
from . import __version__
from .services import asset_path, esp_post, known_wifi_networks, known_wifi_password, printer_status, serial_ports
from .translations import LANGUAGES, tr

MODELS = ["K2 Plus", "K2", "K1 Max", "K1C", "K1", "Ender-3 V3 Plus",
          "Ender-3 V3", "Ender-3 V3 KE", "Ender-3 V3 SE", "Hi", "Hi Combo",
          "SparkX i7", "Other Moonraker / Klipper"]

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

def card():
    f = QFrame(); f.setObjectName("card"); f.setLayout(QVBoxLayout())
    f.layout().setContentsMargins(20, 18, 20, 18); f.layout().setSpacing(12)
    return f

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings()
        self.lang = self.settings.value("language", "en")
        self.printers = json.loads(self.settings.value("printers", "[]"))
        self.pool = QThreadPool.globalInstance()
        self.cards = {}
        self.setWindowTitle(f"Hackman3D LayerShot — {__version__}")
        self.setMinimumSize(1050, 720); self.resize(1240, 820)
        self._build()
        self._refresh_printer_cards()
        self.poller = QTimer(self); self.poller.timeout.connect(self.refresh_all); self.poller.start(5000)

    def T(self, key): return tr(self.lang, key)
    def open_url(self, url): QDesktopServices.openUrl(QUrl(url))
    def label(self, text, kind=None):
        w = QLabel(text); w.setWordWrap(True)
        if kind: w.setObjectName(kind)
        return w

    def _build(self):
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); row = QHBoxLayout(top); row.setContentsMargins(22,12,22,12)
        logo = QLabel(); logo.setFixedSize(42,42)
        icon = asset_path("Hackman3DLayerShot.png")
        if icon.exists():
            from PySide6.QtGui import QPixmap
            logo.setPixmap(QPixmap(str(icon)).scaled(42,42,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        row.addWidget(logo); row.addWidget(self.label("Hackman3D LayerShot", "brand")); row.addStretch()
        for text, url in [("YouTube","https://youtube.com/@hackman3d"),("Instagram","https://instagram.com/hackman3d"),
                          ("TikTok","https://tiktok.com/@hackman3d"),("PayPal","https://paypal.me/hackman3d")]:
            row.addWidget(button(text, lambda checked=False, u=url: self.open_url(u)))
        self.language = QComboBox()
        for name, code in LANGUAGES: self.language.addItem(name, code)
        idx = max(0, self.language.findData(self.lang)); self.language.setCurrentIndex(idx)
        self.language.currentIndexChanged.connect(self.change_language); row.addWidget(self.language)
        outer.addWidget(top)
        support = QFrame(); support.setObjectName("support"); sr = QHBoxLayout(support)
        sr.addWidget(self.label(self.T("support"))); sr.addStretch()
        sr.addWidget(button("PayPal", lambda: self.open_url("https://paypal.me/hackman3d"), True))
        outer.addWidget(support)
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        nav = QFrame(); nav.setObjectName("sidebar"); nav.setFixedWidth(210); nv = QVBoxLayout(nav)
        nv.setContentsMargins(10,18,10,18)
        self.nav_buttons = []
        for key in ("printers","setup","timelapse","about"):
            b = button(self.T(key)); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False, i=len(self.nav_buttons): self.show_page(i))
            self.nav_buttons.append(b); nv.addWidget(b)
        nv.addStretch(); nv.addWidget(self.label(f"v{__version__}", "subtitle"))
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_printers_page()); self.stack.addWidget(self.build_setup_page())
        self.stack.addWidget(self.build_timelapse_page()); self.stack.addWidget(self.build_about_page())
        body.addWidget(nav); body.addWidget(self.stack, 1); outer.addLayout(body, 1)
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
        p = card(); p.layout().addWidget(self.label(self.T("printer_step"), "section"))
        form = QFormLayout()
        self.p_name = QLineEdit(); self.p_name.setPlaceholderText("Workshop K2")
        self.p_model = QComboBox(); self.p_model.addItems(MODELS)
        self.p_host = QLineEdit(); self.p_host.setPlaceholderText("192.168.1.51")
        self.p_port = QSpinBox(); self.p_port.setRange(1,65535); self.p_port.setValue(7125)
        for key,w in [("name",self.p_name),("model",self.p_model),("address",self.p_host),("port",self.p_port)]:
            form.addRow(self.T(key),w)
        p.layout().addLayout(form)
        pr = QHBoxLayout(); pr.addWidget(button(self.T("test"), self.test_printer)); pr.addWidget(button(self.T("save"), self.save_printer, True)); pr.addStretch()
        p.layout().addLayout(pr); self.test_result = self.label(""); p.layout().addWidget(self.test_result); lay.addWidget(p)
        e = card(); e.layout().addWidget(self.label(self.T("esp_step"), "section"))
        ef = QFormLayout(); self.port_combo = QComboBox(); self.refresh_ports()
        ef.addRow(self.T("serial"), self.port_combo); e.layout().addLayout(ef)
        er = QHBoxLayout(); er.addWidget(button(self.T("detect"), self.refresh_ports)); er.addWidget(button(self.T("flash"), self.flash_firmware, True)); er.addStretch()
        e.layout().addLayout(er); self.flash_progress = QProgressBar(); self.flash_progress.setValue(0); e.layout().addWidget(self.flash_progress); lay.addWidget(e)
        w = card(); w.layout().addWidget(self.label(self.T("wifi_step"), "section")); wf = QFormLayout()
        self.ssid = QComboBox(); self.ssid.setEditable(True); self.ssid.addItems(known_wifi_networks())
        self.ssid.currentTextChanged.connect(self.fill_known_password)
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.esp_host = QLineEdit("hackmanlayershot.local")
        wf.addRow(self.T("ssid"),self.ssid); wf.addRow(self.T("password"),self.password); wf.addRow(self.T("esp_address"),self.esp_host)
        w.layout().addLayout(wf); wr = QHBoxLayout()
        wr.addWidget(button(self.T("configure"), self.configure_esp, True)); wr.addWidget(button(self.T("pair"), self.pair_iphone)); wr.addWidget(button(self.T("shot"), self.test_shutter)); wr.addStretch()
        w.layout().addLayout(wr); w.layout().addWidget(self.label(self.T("tip"), "good")); lay.addWidget(w); lay.addStretch()
        return page

    def build_timelapse_page(self):
        page, lay = self.page_shell(self.T("time_title")); c = card(); form = QFormLayout()
        self.photos = QLineEdit(); self.video = QLineEdit()
        pr = QHBoxLayout(); pr.addWidget(self.photos,1); pr.addWidget(button(self.T("choose"),self.choose_photos))
        vr = QHBoxLayout(); vr.addWidget(self.video,1); vr.addWidget(button(self.T("choose"),self.choose_video))
        self.fps = QSpinBox(); self.fps.setRange(1,60); self.fps.setValue(30)
        self.ratio = QComboBox(); self.ratio.addItems(["16:9 (1920×1080)","9:16 (1080×1920)","1:1 (1080×1080)","Original"])
        self.framing = QComboBox(); self.framing.addItems([self.T("fit"),self.T("fill"),self.T("stretch")])
        form.addRow(self.T("photos"),pr); form.addRow(self.T("output"),vr); form.addRow(self.T("fps"),self.fps)
        form.addRow(self.T("ratio"),self.ratio); form.addRow(self.T("framing"),self.framing)
        c.layout().addLayout(form); c.layout().addWidget(button(self.T("render"), self.render_video, True))
        self.render_progress = QProgressBar(); c.layout().addWidget(self.render_progress); lay.addWidget(c); lay.addStretch()
        return page

    def build_about_page(self):
        page, lay = self.page_shell(self.T("about")); c = card()
        c.layout().addWidget(self.label("Hackman3D LayerShot", "title"))
        c.layout().addWidget(self.label(f"{self.T('version')} {__version__}", "good"))
        c.layout().addWidget(self.label(self.T("support"))); c.layout().addWidget(self.label(self.T("about_text"), "section"))
        r = QHBoxLayout()
        for text,url in [("YouTube","https://youtube.com/@hackman3d"),("Instagram","https://instagram.com/hackman3d"),
                         ("TikTok","https://tiktok.com/@hackman3d"),("Creality Cloud","https://www.crealitycloud.com"),
                         ("PayPal","https://paypal.me/hackman3d"),(self.T("feedback"),"mailto:hackman3d@gmail.com")]:
            r.addWidget(button(text, lambda checked=False,u=url:self.open_url(u)))
        r.addStretch(); c.layout().addLayout(r); lay.addWidget(c); lay.addStretch(); return page

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav_buttons): b.setChecked(i == index)

    def change_language(self):
        code = self.language.currentData()
        if code == self.lang: return
        self.settings.setValue("language", code)
        QMessageBox.information(self, "LayerShot", "The new language will be applied after restarting the app.")

    def run(self, fn, args=(), done=None, failed=None):
        worker = Worker(fn,*args)
        if done: worker.signals.done.connect(done)
        worker.signals.failed.connect(failed or (lambda error: QMessageBox.warning(self,"LayerShot",error)))
        self.pool.start(worker)

    def save_printer(self):
        host = self.p_host.text().strip()
        if not host: return
        item={"id":host+":"+str(self.p_port.value()),"name":self.p_name.text().strip() or self.p_model.currentText(),
              "model":self.p_model.currentText(),"host":host,"port":self.p_port.value()}
        self.printers=[p for p in self.printers if p["id"] != item["id"]]+[item]
        self.settings.setValue("printers",json.dumps(self.printers)); self._refresh_printer_cards(); self.show_page(0); self.refresh_all()

    def test_printer(self):
        self.test_result.setText("Connecting…")
        self.run(printer_status,(self.p_host.text().strip(),self.p_port.value()),
                 lambda _:self.test_result.setText("✓ "+self.T("online")),
                 lambda e:self.test_result.setText("✕ "+e))

    def _refresh_printer_cards(self):
        while self.printer_grid.count():
            w=self.printer_grid.takeAt(0).widget()
            if w: w.deleteLater()
        self.cards={}
        if not self.printers:
            self.printer_grid.addWidget(self.label(self.T("no_printer"),"subtitle"),0,0); return
        for i,p in enumerate(self.printers):
            c=card(); c.layout().addWidget(self.label(p["name"],"section")); c.layout().addWidget(self.label(p["model"],"subtitle"))
            state=self.label(self.T("offline"),"bad"); c.layout().addWidget(state)
            detail=self.label(f"{p['host']}:{p['port']}\n{self.T('status')}: —\n{self.T('progress')}: —"); c.layout().addWidget(detail)
            bar=QProgressBar(); c.layout().addWidget(bar); r=QHBoxLayout()
            r.addWidget(button(self.T("camera"),lambda checked=False,x=p:self.open_url(f"http://{x['host']}:{x['port']}")))
            r.addWidget(button(self.T("remove"),lambda checked=False,x=p:self.remove_printer(x["id"]))); c.layout().addLayout(r)
            self.printer_grid.addWidget(c,i//2,i%2); self.cards[p["id"]]=(state,detail,bar)

    def refresh_all(self):
        for p in self.printers:
            self.run(printer_status,(p["host"],p["port"]),lambda data,x=p:self.update_card(x,data),
                     lambda error,x=p:self.fail_card(x,error))

    def update_card(self,p,data):
        if p["id"] not in self.cards:return
        stats,display=data; state,detail,bar=self.cards[p["id"]]
        state.setText("● "+self.T("online")); state.setObjectName("good"); state.style().polish(state)
        filename=stats.get("filename") or "—"; status=stats.get("state") or "ready"; progress=int(float(display.get("progress",0))*100)
        detail.setText(f"{p['host']}:{p['port']}\n{self.T('status')}: {status}\n{filename}\n{self.T('progress')}: {progress}%"); bar.setValue(progress)

    def fail_card(self,p,error):
        if p["id"] in self.cards:
            state,detail,bar=self.cards[p["id"]]; state.setText("● "+self.T("offline")); detail.setText(f"{p['host']}:{p['port']}\n{error}"); bar.setValue(0)

    def remove_printer(self,pid):
        self.printers=[p for p in self.printers if p["id"]!=pid]; self.settings.setValue("printers",json.dumps(self.printers)); self._refresh_printer_cards()
    def refresh_ports(self):
        if not hasattr(self,"port_combo"): return
        current=self.port_combo.currentText(); self.port_combo.clear(); self.port_combo.addItems(serial_ports())
        if current:self.port_combo.setCurrentText(current)
    def fill_known_password(self,ssid):
        if ssid and not self.password.text(): self.password.setText(known_wifi_password(ssid))

    def flash_firmware(self):
        port=self.port_combo.currentText()
        if not port: QMessageBox.warning(self,"LayerShot","Connect the ESP32-C3 and select its USB port."); return
        fw=asset_path("Hackman3DLayerShot.bin")
        exe=shutil.which("esptool") or shutil.which("esptool.py")
        if not fw.exists() or not exe: QMessageBox.warning(self,"LayerShot","Firmware tools are missing from this development build."); return
        self.flash_progress.setRange(0,0)
        def task():
            subprocess.run([exe,"--chip","esp32c3","--port",port,"write_flash","0x0",str(fw)],check=True,capture_output=True,text=True)
            return True
        self.run(task,done=lambda _: (self.flash_progress.setRange(0,100),self.flash_progress.setValue(100),QMessageBox.information(self,"LayerShot","Firmware installed.")),
                 failed=lambda e:(self.flash_progress.setRange(0,100),QMessageBox.warning(self,"LayerShot",e)))

    def configure_esp(self):
        host=self.esp_host.text().strip().removeprefix("http://").rstrip("/")
        def task():
            if self.printers:
                printer=self.printers[0]
                esp_post(host,"printer-config",{"host":printer["host"],"port":printer["port"],
                         "every":1,"skip":0,"stop":0,"delay":800})
            return esp_post(host,"configure",{"ssid":self.ssid.currentText(),"password":self.password.text()})
        self.run(task,done=lambda _:QMessageBox.information(self,"LayerShot","Settings stored in the ESP32. It is restarting now."))
    def pair_iphone(self):
        self.run(esp_post,(self.esp_host.text().strip(),"pair",{}),lambda _:QMessageBox.information(self,"LayerShot","Pairing is active for 60 seconds. Open iPhone Bluetooth settings."))
    def test_shutter(self): self.run(esp_post,(self.esp_host.text().strip(),"trigger",{}),lambda _:QMessageBox.information(self,"LayerShot","Shutter command sent."))
    def choose_photos(self): self.photos.setText(QFileDialog.getExistingDirectory(self,self.T("photos")))
    def choose_video(self):
        f,_=QFileDialog.getSaveFileName(self,self.T("output"),"layershot-timelapse.mp4","MP4 video (*.mp4)")
        if f:self.video.setText(f)
    def render_video(self):
        ffmpeg=shutil.which("ffmpeg")
        photos=Path(self.photos.text()); output=self.video.text()
        if not ffmpeg or not photos.is_dir() or not output:
            QMessageBox.warning(self,"LayerShot","Select a photo folder and output file. FFmpeg must be installed."); return
        images=sorted([p for p in photos.iterdir() if p.suffix.lower() in (".jpg",".jpeg",".png")])
        if not images: QMessageBox.warning(self,"LayerShot","No compatible photos found."); return
        manifest=photos/".layershot-input.txt"; manifest.write_text("".join(f"file '{str(p).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in images))
        self.render_progress.setRange(0,0)
        def task():
            subprocess.run([ffmpeg,"-y","-r",str(self.fps.value()),"-f","concat","-safe","0","-i",str(manifest),"-pix_fmt","yuv420p",output],check=True,capture_output=True)
            manifest.unlink(missing_ok=True); return True
        self.run(task,done=lambda _:(self.render_progress.setRange(0,100),self.render_progress.setValue(100),QMessageBox.information(self,"LayerShot","Timelapse created.")),
                 failed=lambda e:(self.render_progress.setRange(0,100),QMessageBox.warning(self,"LayerShot",e)))
