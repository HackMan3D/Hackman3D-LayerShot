# Hackman3D LayerShot

Hackman3D LayerShot transforme un ESP32-C3 en déclencheur Bluetooth autonome pour réaliser des timelapses d’impression 3D avec l’app Appareil photo d’un iPhone.

L’application de bureau sert à installer et configurer le boîtier, surveiller une ou plusieurs imprimantes Creality/Klipper et assembler les photos. Une fois la configuration envoyée à l’ESP32, l’application n’a pas besoin de rester ouverte pendant l’impression.

## Fonctions

- déclenchement de l’obturateur iPhone par Bluetooth HID (« Volume + ») ;
- appairage et effacement des associations depuis le bouton BOOT de l’ESP32 ;
- fonctionnement autonome avec détection des changements de couche via Moonraker ;
- prise en charge des familles Creality K2, K1, Ender, CR et SPARKX i7 ;
- tableau de bord multi-imprimantes avec état et accès à la caméra si disponible ;
- configuration Wi-Fi, imprimante, fréquence, stabilisation et limites de capture ;
- génération de timelapse et options de cadrage ;
- applications macOS et Windows, plus firmware ESP32-C3 ;
- interface multilingue côté macOS.

## Matériel

- carte ESP32-C3 compacte avec 4 Mo de flash ;
- iPhone compatible avec les télécommandes Bluetooth ;
- imprimante accessible sur le même réseau local et exposant l’API Moonraker.

Le firmware utilise le nom réseau `hackman-layershot.local` et le nom Bluetooth `Hackman3D LayerShot`.

## Utilisation rapide

1. Flasher le firmware avec l’application de bureau.
2. Connecter le Mac ou le PC au réseau Wi-Fi temporaire `Hackman3D-LayerShot`.
3. Envoyer au boîtier le Wi-Fi de la maison et l’adresse de l’imprimante.
4. Maintenir BOOT environ 3 secondes, puis sélectionner `Hackman3D LayerShot` dans Réglages > Bluetooth sur l’iPhone.
5. Ouvrir l’app Appareil photo et lancer l’impression.

Une pression courte sur BOOT active l’appairage. Un appui d’au moins 10 secondes efface les anciens appareils Bluetooth.

## Construire les applications

### macOS

Prérequis : macOS et Swift.

```sh
zsh scripts/build-app.sh
open "outputs/Hackman3D LayerShot.app"
```

### Windows

Prérequis : SDK .NET 8.

```powershell
dotnet publish .\windows\Hackman3D.LayerShot.Windows\Hackman3D.LayerShot.Windows.csproj `
  -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

Consultez [windows/README.md](windows/README.md) pour ARM64 et les outils facultatifs.

## Construire le firmware

Ouvrir `firmware/Hackman3DLayerShot/Hackman3DLayerShot.ino` dans Arduino IDE avec le cœur Espressif ESP32 et sélectionner la carte correspondant à l’ESP32-C3.

Le firmware ne contient aucun identifiant Wi-Fi. Les réglages saisis sont enregistrés localement dans la mémoire non volatile de l’ESP32.

## Soutenir le projet

Le logiciel est fourni gratuitement. Les dons, retours et abonnements aux réseaux Hackman3D sont les bienvenus depuis le bandeau permanent de l’application.

Créé, designé et codé par Hackman3D.

## État du projet

Version de développement. Le dépôt est actuellement privé et aucune licence de redistribution n’est accordée tant qu’un fichier `LICENSE` n’a pas été ajouté.
