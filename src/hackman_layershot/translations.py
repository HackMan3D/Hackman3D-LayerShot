LANGUAGES = [
    ("English", "en"), ("Français", "fr"), ("Italiano", "it"), ("Español", "es"),
    ("Português", "pt"), ("中文", "zh"), ("Deutsch", "de"), ("हिन्दी", "hi"),
    ("العربية", "ar"), ("বাংলা", "bn"), ("Bahasa Indonesia", "id"),
    ("Русский", "ru"), ("日本語", "ja"), ("한국어", "ko"), ("Türkçe", "tr"),
    ("Tiếng Việt", "vi"), ("ไทย", "th"),
]

TEXT = {
 "en": {
  "printers":"Printers","setup":"Installation","timelapse":"Timelapse","about":"About",
  "support":"LayerShot is provided free of charge. Donations and subscriptions help keep the project alive.",
  "open":"Open","refresh":"Refresh now","add":"Add printer","name":"Printer name",
  "model":"Creality model","address":"Network address","port":"Port","save":"Save printer",
  "test":"Test connection","remove":"Remove","camera":"Open camera","online":"Connected",
  "offline":"Offline","status":"Status","progress":"Progress","layer":"Layer",
  "setup_title":"Install and configure LayerShot","printer_step":"1. Add your printer",
  "esp_step":"2. Flash the ESP32-C3","serial":"USB serial port","detect":"Refresh ports",
  "flash":"Install firmware","wifi_step":"3. Configure autonomous operation",
  "ssid":"Wi-Fi network","password":"Wi-Fi password","esp_address":"ESP address",
  "configure":"Send settings to ESP","pair":"Enable iPhone pairing","shot":"Test camera shutter",
  "tip":"The Mac/PC app is not required during printing. Settings are stored in the ESP32.",
  "time_title":"Create a timelapse","photos":"Photos folder","choose":"Choose…",
  "output":"Output file","fps":"Frames per second","ratio":"Aspect ratio","framing":"Framing",
  "fit":"Fit (no crop)","fill":"Fill (crop)","stretch":"Stretch","render":"Create timelapse",
  "about_text":"Created, designed and coded by HackMan3D.","feedback":"Send feedback",
  "version":"Version","no_printer":"No printer has been added yet.",
 },
 "fr": {
  "printers":"Imprimantes","setup":"Installation","timelapse":"Timelapse","about":"À propos",
  "support":"LayerShot est fourni gratuitement. Les dons et abonnements aident le projet à continuer.",
  "open":"Ouvrir","refresh":"Actualiser","add":"Ajouter une imprimante","name":"Nom de l’imprimante",
  "model":"Modèle Creality","address":"Adresse réseau","port":"Port","save":"Enregistrer",
  "test":"Tester la connexion","remove":"Supprimer","camera":"Ouvrir la caméra","online":"Connectée",
  "offline":"Hors ligne","status":"État","progress":"Progression","layer":"Couche",
  "setup_title":"Installer et configurer LayerShot","printer_step":"1. Ajouter votre imprimante",
  "esp_step":"2. Flasher l’ESP32-C3","serial":"Port série USB","detect":"Actualiser les ports",
  "flash":"Installer le firmware","wifi_step":"3. Configurer le fonctionnement autonome",
  "ssid":"Réseau Wi-Fi","password":"Mot de passe Wi-Fi","esp_address":"Adresse de l’ESP",
  "configure":"Envoyer les réglages à l’ESP","pair":"Activer l’appairage iPhone","shot":"Tester l’obturateur",
  "tip":"L’app Mac/PC n’est pas nécessaire pendant l’impression. Les réglages sont enregistrés dans l’ESP32.",
  "time_title":"Créer un timelapse","photos":"Dossier des photos","choose":"Choisir…",
  "output":"Fichier de sortie","fps":"Images par seconde","ratio":"Format","framing":"Cadrage",
  "fit":"Ajuster (sans recadrage)","fill":"Remplir (recadrer)","stretch":"Étirer","render":"Créer le timelapse",
  "about_text":"Créé, designé et codé par HackMan3D.","feedback":"Envoyer un feedback",
  "version":"Version","no_printer":"Aucune imprimante n’a encore été ajoutée.",
 },
}

def tr(lang, key):
    return TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"].get(key, key))
