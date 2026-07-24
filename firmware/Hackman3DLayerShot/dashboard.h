#pragma once

static const char LAYERSHOT_DASHBOARD[] PROGMEM = R"HTML(
<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hackman3D LayerShot</title>
<style>
:root{color-scheme:dark;--bg:#0c1018;--panel:#171d29;--line:#2e3849;--text:#f4f7fb;--muted:#9da8b9;--blue:#1595ff;--green:#35d07f;--red:#ff5c68}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#0b0f17,#111827);color:var(--text);font:15px system-ui,-apple-system,sans-serif}
main{max-width:1050px;margin:auto;padding:28px 18px 50px}header{display:flex;align-items:center;gap:15px;margin-bottom:24px}
.logo{display:grid;place-items:center;width:54px;height:54px;border-radius:15px;background:#062b49;color:#55c5ff;font-size:28px;font-weight:900}
h1{font-size:25px;margin:0}header p{margin:4px 0;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.card{background:rgba(23,29,41,.96);border:1px solid var(--line);border-radius:18px;padding:19px;box-shadow:0 16px 45px #0004}
.wide{grid-column:1/-1}.title{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.title h2{font-size:18px;margin:0}
.badge{padding:6px 10px;border-radius:999px;background:#242c3a;color:var(--muted);font-weight:700}.ok{color:var(--green)}.bad{color:var(--red)}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.metric{background:#0e131c;border-radius:12px;padding:13px}.metric small{display:block;color:var(--muted);margin-bottom:6px}.metric strong{font-size:19px}
label{display:block;color:var(--muted);margin:11px 0 6px}input{width:100%;border:1px solid var(--line);border-radius:11px;background:#0e131c;color:var(--text);padding:11px 12px;font:inherit}
.row{display:grid;grid-template-columns:1fr 130px;gap:10px}.actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}
button{border:1px solid #3b4659;border-radius:11px;background:#252e3e;color:#fff;padding:10px 14px;font-weight:750;cursor:pointer}button.primary{background:var(--blue);border-color:var(--blue)}button.danger{background:#4b242a;border-color:#78343c}
.help{color:var(--muted);line-height:1.5;margin:10px 0 0}.message{min-height:22px;color:#66c9ff;margin-top:12px}
footer{text-align:center;color:#727d8e;margin-top:24px}@media(max-width:720px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}.metrics{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
</style></head><body><main>
<header><div class="logo">LS</div><div><h1>Hackman3D LayerShot</h1><p id="identity">Chargement…</p></div></header>
<section class="grid">
<article class="card"><div class="title"><h2>Wi-Fi</h2><span class="badge" id="wifiBadge">…</span></div>
<div class="metrics"><div class="metric"><small>Réseau</small><strong id="ssid">—</strong></div><div class="metric"><small>Adresse IP</small><strong id="ip">—</strong></div><div class="metric"><small>Signal</small><strong id="rssi">—</strong></div></div>
<form id="wifiForm"><label>Nouveau réseau Wi-Fi</label><input name="ssid" required placeholder="Nom du réseau"><label>Mot de passe</label><div class="row"><input id="wifiPassword" name="password" type="password" placeholder="Mot de passe"><button type="button" onclick="togglePassword()">Afficher</button></div><div class="actions"><button class="primary">Enregistrer et redémarrer</button></div></form></article>
	<article class="card"><div class="title"><h2>Caméra · <span id="cameraName">—</span></h2><span class="badge" id="bleBadge">…</span></div>
	<p class="help" id="pairingHelp">Chargement des instructions d’appairage…</p>
	<div class="actions"><button class="primary" onclick="post('/pair')">Démarrer l’appairage</button><button onclick="post('/trigger')">Tester l’obturateur</button><button onclick="post('/led-test')">Tester la LED</button><button class="danger" onclick="post('/reset-bonds')">Oublier la caméra</button></div></article>
<article class="card wide"><div class="title"><h2>Imprimante et détection des couches</h2><span class="badge" id="printerBadge">…</span></div>
<div class="metrics"><div class="metric"><small>État</small><strong id="printerState">—</strong></div><div class="metric"><small>Couche</small><strong id="layer">—</strong></div><div class="metric"><small>Déclenchements</small><strong id="triggers">0</strong></div></div>
<p class="help">Dernière commande reçue : <b id="lastCommand">—</b> · Total des commandes : <b id="commands">0</b></p>
<form id="printerForm"><div class="row"><div><label>Adresse de l’imprimante</label><input name="host" id="printerHost" required placeholder="192.168.1.51"></div><div><label>Port</label><input name="port" id="printerPort" type="number" value="4408"></div></div>
<input type="hidden" name="every" value="1"><input type="hidden" name="skip" value="0"><input type="hidden" name="stop" value="0"><input type="hidden" name="delay" value="800">
<div class="actions"><button class="primary">Enregistrer</button><button type="button" onclick="post('/printer-test')">Tester la détection</button></div></form></article>
</section><div class="message" id="message"></div><footer>Créé, designé et codé par Hackman3D · Firmware <span id="firmware">—</span></footer>
</main><script>
const $=id=>document.getElementById(id);const say=t=>$('message').textContent=t;
function togglePassword(){let p=$('wifiPassword');p.type=p.type==='password'?'text':'password'}
async function post(url,data){try{let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:data?new URLSearchParams(data):''});let j=await r.json();say(j.ok?'Commande effectuée.':('Erreur : '+(j.error||r.status)));setTimeout(refresh,400)}catch(e){say('Connexion impossible : '+e.message)}}
async function refresh(){try{let s=await (await fetch('/status',{cache:'no-store'})).json();
	$('identity').textContent=s.hostname+' · '+s.ip;$('firmware').textContent=s.firmware;$('ssid').textContent=s.ssid||'Non configuré';$('ip').textContent=s.ip;$('rssi').textContent=s.wifi?(s.rssi+' dBm'):'—';
	$('wifiBadge').textContent=s.wifi?'Connecté':'Déconnecté';$('wifiBadge').className='badge '+(s.wifi?'ok':'bad');
	$('cameraName').textContent=s.camera_name||'Smartphone';$('bleBadge').textContent=s.bluetooth?'Caméra connectée':(s.pairing?'Appairage actif':'Déconnectée');$('bleBadge').className='badge '+(s.bluetooth?'ok':'bad');
	$('pairingHelp').innerHTML=s.camera_type==='android'?'Sur Android, ouvrez Paramètres › Appareils connectés › Associer un nouvel appareil, sélectionnez <b>Hackman3D LayerShot</b>, puis ouvrez l’appareil photo. Réglez les touches de volume sur Déclencheur si nécessaire.': 'Sur l’iPhone, ouvrez Réglages › Bluetooth, sélectionnez <b>Hackman3D LayerShot</b>, puis ouvrez l’app Appareil photo. Bouton BOOT : appui court = photo, 3 secondes = appairage, 10 secondes = oubli.';
$('printerBadge').textContent=s.printer_connected?'Détectée':'Non détectée';$('printerBadge').className='badge '+(s.printer_connected?'ok':'bad');
$('printerState').textContent=s.printer_state||'Inconnue';$('layer').textContent=s.current_layer>=0?(s.current_layer+(s.total_layers>0?' / '+s.total_layers:'')):'—';$('triggers').textContent=s.triggers;
$('lastCommand').textContent=s.last_command||'—';$('commands').textContent=s.commands||0;
if(document.activeElement.tagName!=='INPUT'){$('printerHost').value=s.printer||'';$('printerPort').value=s.printer_port||4408}
}catch(e){say('Le tableau de bord ne répond pas.')}}setInterval(refresh,2000);refresh();
$('wifiForm').onsubmit=e=>{e.preventDefault();post('/configure',Object.fromEntries(new FormData(e.target)))};
$('printerForm').onsubmit=e=>{e.preventDefault();post('/printer-config',Object.fromEntries(new FormData(e.target)))};
</script></body></html>
)HTML";
