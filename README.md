# FFmpeg Converter / FFmpeg Konverter (Windows 11, PySide6)

EN: Desktop GUI to analyze and batch-convert media files with `ffmpeg`/`ffprobe`.

DE: Desktop-GUI zur Analyse und Batch-Konvertierung von Mediendateien mit `ffmpeg`/`ffprobe`.

## 1) Features (EN)

- Multi-page UI (tabs):
  - `1) Source & Media`
  - `2) Conversion`
  - `3) Summary`
  - `4) Progress & Log`
  - `5) Hardware & Codecs`
- Language switch (English/German) on page 1
  - Default language: English
  - Persisted in config
- Source/target folder selection
- Recursive scan option
- `ffprobe` analysis:
  - duration, resolution, FPS, bitrate
  - video codec, audio codec, channels
- File table with checkbox per file
- Filters:
  - filename filter
  - extension filter
- Selection controls:
  - select all/none
  - priority up/down
  - convert only visible selection
  - convert only changed files since last successful run
- Export modes:
  - Video + Audio
  - Audio Only
  - Video Only
- Output formats:
  - Video: `mp4`, `mov`, `avi`, `asf`, `flv`, `mkv`, `webm`, `mpg`
  - Audio: `mp3`, `wav`, `flac`, `m4a`, `aac`, `opus`, `wma`
- Encoders (depending on ffmpeg build/runtime):
  - CPU: `libx264`, `libx265`
  - AMD GPU: `h264_amf`, `hevc_amf`
  - NVIDIA GPU: `h264_nvenc`, `hevc_nvenc`
  - Intel GPU: `h264_qsv`, `hevc_qsv`
- AMF options:
  - `-quality` (`speed`/`quality`)
  - `-rc vbr_peak`
  - `-b:v`, `-maxrate`, `-bufsize`
  - `-pix_fmt yuv420p`
- Audio behavior:
  - `copy` keeps original audio
  - `aac stereo`: `-c:a aac -b:a 192k -ac 2`
  - `aac 5.1`: `-c:a aac -b:a 384k -ac 6`
  - Opus in MP4 is auto-corrected to AAC
  - downmix on demand
- Central bitrate profile by resolution:
  - `<= 720x400`: `2800k`
  - `<= 1280x720`: `6000k`
  - `>= 1080p`: `9000k`
  - derived `maxrate` and `bufsize`
- Presets:
  - built-in presets
  - custom presets (save/delete/import/export)
  - preset lock handling
  - preset favorites + favorites-only filter
- Auto presets:
  - generate all compatible presets
  - generate top 5 recommended presets
  - target profile selector: `General`, `Smartphone`, `TV`, `YouTube`, `Archive`
  - reset generated auto presets only (manual custom presets remain untouched)
- Batch templates:
  - save/load/delete complete job templates
- Queue and processing:
  - parallel jobs: `1..3`
  - non-freezing GUI via `QThread` + signals
  - ffmpeg progress via `-progress pipe:1`
  - per-file progress + global progress
  - speed/ETA/size columns
  - pause/resume queue
  - retry failed jobs
  - continue on file error
- Naming and conflict handling:
  - prefix/suffix
  - optional timestamp
  - mirror source subfolders
  - conflict policy: number/skip/overwrite
  - optional strict protection: abort start if target exists
- Live preflight hints:
  - target conflict warning in summary
  - estimated output size per file and total
- Analysis export:
  - JSON/CSV (optional feature toggle)
- Job report export:
  - JSON report after queue (optional feature toggle)
- Optional drag & drop source selection
- Hardware & codec diagnostics tab:
  - runtime capability checks (AMF/NVENC/QSV)
  - build availability vs runtime availability
  - CPU/GPU vendor detection (AMD/Intel/NVIDIA)
  - available encoder/decoder overview
  - hardware stability test (short ffmpeg tests)
- ffmpeg auto-install on startup when missing:
  - popup prompt
  - background install via `winget`
  - waiting dialog with status updates
  - repeated binary checks
  - optional app restart if needed
- Persistent config with migration:
  - `%APPDATA%\FFmpeg-Konverter\config.json`
  - migrates legacy local config when possible

## 2) Funktionen (DE)

- Mehrseitige Oberfläche (Tabs):
  - `1) Quelle & Medien`
  - `2) Konvertierung`
  - `3) Zusammenfassung`
  - `4) Fortschritt & Log`
  - `5) Hardware & Codecs`
- Sprachauswahl (Englisch/Deutsch) auf Seite 1
  - Standardsprache: Englisch
  - wird in der Konfiguration gespeichert
- Quell-/Zielordner-Auswahl
- Optional rekursiver Scan
- `ffprobe`-Analyse:
  - Dauer, Auflösung, FPS, Bitrate
  - Video-Codec, Audio-Codec, Kanäle
- Dateitabelle mit Checkbox pro Datei
- Filter:
  - Dateiname
  - Dateiendung
- Auswahlsteuerung:
  - Alle/Keine markieren
  - Priorität hoch/runter
  - nur sichtbare Auswahl konvertieren
  - nur geänderte Dateien seit letztem erfolgreichen Lauf
- Exportmodi:
  - Video + Audio
  - Nur Audio
  - Nur Video
- Ausgabeformate:
  - Video: `mp4`, `mov`, `avi`, `asf`, `flv`, `mkv`, `webm`, `mpg`
  - Audio: `mp3`, `wav`, `flac`, `m4a`, `aac`, `opus`, `wma`
- Encoder (abhängig von ffmpeg-Build/Laufzeit):
  - CPU: `libx264`, `libx265`
  - AMD GPU: `h264_amf`, `hevc_amf`
  - NVIDIA GPU: `h264_nvenc`, `hevc_nvenc`
  - Intel GPU: `h264_qsv`, `hevc_qsv`
- AMF-Optionen:
  - `-quality` (`speed`/`quality`)
  - `-rc vbr_peak`
  - `-b:v`, `-maxrate`, `-bufsize`
  - `-pix_fmt yuv420p`
- Audio-Verhalten:
  - `copy` übernimmt Originalton
  - `aac stereo`: `-c:a aac -b:a 192k -ac 2`
  - `aac 5.1`: `-c:a aac -b:a 384k -ac 6`
  - Opus in MP4 wird automatisch auf AAC korrigiert
  - Downmix bei Bedarf
- Zentrale Bitratenlogik nach Auflösung:
  - `<= 720x400`: `2800k`
  - `<= 1280x720`: `6000k`
  - `>= 1080p`: `9000k`
  - passende `maxrate` und `bufsize`
- Presets:
  - eingebaute Presets
  - Custom Presets (speichern/löschen/importieren/exportieren)
  - Preset-Lock
  - Preset-Favoriten + Nur-Favoriten-Filter
- Auto-Presets:
  - alle kompatiblen Presets generieren
  - Top-5-Empfehlungen generieren
  - Zielprofil-Auswahl: `Allgemein`, `Smartphone`, `TV`, `YouTube`, `Archiv`
  - nur generierte Auto-Presets zurücksetzen (manuelle bleiben)
- Batch-Templates:
  - komplette Job-Setups speichern/laden/löschen
- Queue und Verarbeitung:
  - Parallel-Jobs: `1..3`
  - GUI friert nicht ein (`QThread` + Signals)
  - ffmpeg-Fortschritt via `-progress pipe:1`
  - Fortschritt pro Datei + global
  - Spalten für Speed/ETA/Size
  - Queue pausieren/fortsetzen
  - fehlgeschlagene Jobs erneut starten
  - bei Dateifehlern mit nächster Datei weitermachen
- Dateinamen- und Konfliktbehandlung:
  - Prefix/Suffix
  - optional Zeitstempel
  - Unterordnerstruktur spiegeln
  - Konfliktmodus: nummerieren/überspringen/überschreiben
  - optional strikter Schutz: Startabbruch bei vorhandenen Zieldateien
- Live-Vorschau/Preflight:
  - Zielkonflikt-Warnung in Zusammenfassung
  - geschätzte Ausgabegröße pro Datei und gesamt
- Analyse-Export:
  - JSON/CSV (optional aktivierbar)
- Job-Report-Export:
  - JSON-Report nach Queue (optional aktivierbar)
- Optionales Drag & Drop für Quelle
- Hardware/Codec-Diagnose-Tab:
  - Runtime-Fähigkeitstests (AMF/NVENC/QSV)
  - Build-Verfügbarkeit vs. Runtime-Verfügbarkeit
  - CPU/GPU-Vendor-Erkennung (AMD/Intel/NVIDIA)
  - verfügbare Encoder/Decoder
  - Hardware-Stabilitätstest (kurze ffmpeg-Tests)
- ffmpeg-Autoinstallation beim Start (falls fehlend):
  - Popup-Abfrage
  - Hintergrundinstallation via `winget`
  - Wartedialog mit Statusmeldungen
  - wiederholte Binärprüfung
  - optionaler App-Neustart
- Persistente Konfiguration mit Migration:
  - `%APPDATA%\FFmpeg-Konverter\config.json`
  - Migration alter lokaler Konfiguration (wenn möglich)

## 3) Requirements / Voraussetzungen

EN:
- Windows 11
- Python 3.10+
- `ffmpeg`/`ffprobe` in `PATH` OR local `ffmpeg.exe`/`ffprobe.exe`
- Optional: `winget` for automatic ffmpeg installation

DE:
- Windows 11
- Python 3.10+
- `ffmpeg`/`ffprobe` im `PATH` ODER lokal als `ffmpeg.exe`/`ffprobe.exe`
- Optional: `winget` für automatische ffmpeg-Installation

## 4) Installation

```powershell
cd F:\ffmpeg-konverter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5) Run / Start

```powershell
cd F:\ffmpeg-konverter
.\.venv\Scripts\Activate.ps1
python main.py
```

## 6) Basic Workflow (EN)

1. Choose source and target folder.
2. Optional: enable recursive scan.
3. Click `Scan / Analyze`.
4. Select files in table.
5. Choose preset or set options manually.
6. Check summary (conflicts/size estimate).
7. Start queue.
8. Monitor progress and log.

## 7) Grundablauf (DE)

1. Quell- und Zielordner wählen.
2. Optional rekursiven Scan aktivieren.
3. `Scan / Analyse starten` klicken.
4. Dateien in Tabelle markieren.
5. Preset wählen oder Einstellungen manuell setzen.
6. Zusammenfassung prüfen (Konflikte/Größenschätzung).
7. Queue starten.
8. Fortschritt und Log beobachten.

## 8) Configuration / Konfiguration

EN:
- Config file path: `%APPDATA%\FFmpeg-Konverter\config.json`
- Stores language, presets, templates, advanced options, runtime state

DE:
- Konfigurationspfad: `%APPDATA%\FFmpeg-Konverter\config.json`
- Speichert Sprache, Presets, Templates, Optionen und Laufzeitstände

## 9) Screenshots / Bildschirmbilder

EN:
- You can add your own screenshots to a folder, e.g. `docs/screenshots/`.
- Recommended screenshots:
  - `01_source_media.png` (tab 1: source/target, scan, file table)
  - `02_conversion.png` (tab 2: export settings, presets, AMF/NVENC/QSV)
  - `03_summary.png` (tab 3: summary, conflict warning, size estimate, start/stop)
  - `04_progress_log.png` (tab 4: file/global progress, log)
  - `05_hardware_codecs.png` (tab 5: runtime checks, auto-preset tools)
- If your repository host supports markdown images, use:
  - `![Source & Media](docs/screenshots/01_source_media.png)`
  - `![Conversion](docs/screenshots/02_conversion.png)`
  - `![Summary](docs/screenshots/03_summary.png)`
  - `![Progress & Log](docs/screenshots/04_progress_log.png)`
  - `![Hardware & Codecs](docs/screenshots/05_hardware_codecs.png)`

DE:
- Du kannst eigene Screenshots in einem Ordner speichern, z. B. `docs/screenshots/`.
- Empfohlene Screenshots:
  - `01_source_media.png` (Tab 1: Quelle/Ziel, Scan, Dateitabelle)
  - `02_conversion.png` (Tab 2: Exporteinstellungen, Presets, AMF/NVENC/QSV)
  - `03_summary.png` (Tab 3: Zusammenfassung, Konfliktwarnung, Größenschätzung, Start/Stopp)
  - `04_progress_log.png` (Tab 4: Datei-/Gesamtfortschritt, Log)
  - `05_hardware_codecs.png` (Tab 5: Runtime-Checks, Auto-Preset-Werkzeuge)
- Wenn dein Repository Markdown-Bilder unterstützt, nutze:
  - `![Quelle & Medien](docs/screenshots/01_source_media.png)`
  - `![Konvertierung](docs/screenshots/02_conversion.png)`
  - `![Zusammenfassung](docs/screenshots/03_summary.png)`
  - `![Fortschritt & Log](docs/screenshots/04_progress_log.png)`
  - `![Hardware & Codecs](docs/screenshots/05_hardware_codecs.png)`

## 10) Example Workflows / Beispiel-Workflows

### A) Fast Daily Conversion (EN)
1. Open tab `1) Source & Media`, choose source and target folders.
2. Click `Scan / Analyze`.
3. Choose preset `MP4 fast small (GPU HEVC)` (or auto-generated MP4 preset).
4. In tab `3) Summary`, verify conflict warning and total size estimate.
5. Click `Start Queue`.
6. Monitor tab `4) Progress & Log`.

### A) Schnelle Alltagskonvertierung (DE)
1. Tab `1) Quelle & Medien` öffnen, Quell- und Zielordner wählen.
2. `Scan / Analyse` klicken.
3. Preset `MP4 schnell klein (GPU HEVC)` wählen (oder automatisch erzeugtes MP4-Preset).
4. In Tab `3) Zusammenfassung` Konfliktwarnung und Gesamtschätzung prüfen.
5. `Queue starten` klicken.
6. Tab `4) Fortschritt & Log` beobachten.

### B) Archive Workflow (EN)
1. In tab `5) Hardware & Codecs`, run runtime checks and (optional) stability test.
2. Generate `Top 5` auto presets with profile `Archive`.
3. Select `AUTO TOP5 ... MKV Archive CPU` or `MKV Archive (x265 CRF18)`.
4. Enable strict target protection (`Target must not be overwritten`).
5. Start queue and export optional JSON report.

### B) Archiv-Workflow (DE)
1. In Tab `5) Hardware & Codecs` Runtime-Checks und optional Stabilitätstest ausführen.
2. `Top 5` Auto-Presets mit Profil `Archiv` erzeugen.
3. `AUTO TOP5 ... MKV Archiv CPU` oder `MKV Archiv (x265 CRF18)` wählen.
4. Strikten Zielschutz aktivieren (`Ziel darf nicht ersetzt werden`).
5. Queue starten und optional JSON-Report exportieren.

### C) Audio-Only Workflow (EN)
1. Set export mode to `Audio Only`.
2. Choose format (`mp3` / `wav` / `flac` / ...).
3. Pick matching audio codec (`mp3`, `wav pcm_s16le`, `flac`, ...).
4. Start queue.

### C) Nur-Audio-Workflow (DE)
1. Exportmodus auf `Nur Audio` setzen.
2. Format wählen (`mp3` / `wav` / `flac` / ...).
3. Passenden Audio-Codec wählen (`mp3`, `wav pcm_s16le`, `flac`, ...).
4. Queue starten.

## 11) Build EXE (PyInstaller)

EN:
- Icon used for EXE: `assets/icon.ico`
- Spec file: `ffmpeg_konverter.spec`
- Build script (recommended):

```powershell
cd F:\ffmpeg-konverter
.\scripts\build_exe.ps1
```

- Output:
  - `dist\FFmpegConverter\FFmpegConverter.exe`

DE:
- Verwendetes EXE-Icon: `assets/icon.ico`
- Spec-Datei: `ffmpeg_konverter.spec`
- Build-Skript (empfohlen):

```powershell
cd F:\ffmpeg-konverter
.\scripts\build_exe.ps1
```

- Ausgabe:
  - `dist\FFmpegConverter\FFmpegConverter.exe`

## 12) Build Installer (Windows Setup + Uninstall)

EN:
- Installer technology: Inno Setup 6
- Script: `installer/FFmpegConverter.iss`
- Build command:

```powershell
cd F:\ffmpeg-konverter
.\scripts\build_installer.ps1
```

- Output:
  - `dist-installer\FFmpegConverter-Setup-<version>.exe`
- Installer behavior:
  - Installs to `%LOCALAPPDATA%\Programs\FFmpeg Converter`
  - Creates `%APPDATA%\FFmpeg-Konverter` at install time
  - Registers uninstall entry in Windows Apps/Installed Apps
  - During normal uninstall, user is asked whether `%APPDATA%\FFmpeg-Konverter` should also be removed
  - Silent uninstall keeps `%APPDATA%\FFmpeg-Konverter` by default
  - Optional uninstall switches:
    - `/DELETEUSERDATA` removes `%APPDATA%\FFmpeg-Konverter` without prompt
    - `/KEEPUSERDATA` keeps `%APPDATA%\FFmpeg-Konverter` without prompt
  - Start Menu shortcut + optional desktop shortcut

DE:
- Installer-Technologie: Inno Setup 6
- Skript: `installer/FFmpegConverter.iss`
- Build-Befehl:

```powershell
cd F:\ffmpeg-konverter
.\scripts\build_installer.ps1
```

- Ausgabe:
  - `dist-installer\FFmpegConverter-Setup-<version>.exe`
- Verhalten des Installers:
  - Installation nach `%LOCALAPPDATA%\Programs\FFmpeg Converter`
  - Legt `%APPDATA%\FFmpeg-Konverter` bei der Installation an
  - Registriert Deinstallation in Windows Apps/Installierte Apps
  - Bei normaler Deinstallation wird gefragt, ob `%APPDATA%\FFmpeg-Konverter` mit entfernt werden soll
  - Bei Silent-Deinstallation bleibt `%APPDATA%\FFmpeg-Konverter` standardmäßig erhalten
  - Optionale Uninstall-Schalter:
    - `/DELETEUSERDATA` entfernt `%APPDATA%\FFmpeg-Konverter` ohne Rückfrage
    - `/KEEPUSERDATA` behält `%APPDATA%\FFmpeg-Konverter` ohne Rückfrage
  - Startmenü-Verknüpfung + optionale Desktop-Verknüpfung

## 13) Full Release Build

EN/DE:

```powershell
cd F:\ffmpeg-konverter
.\scripts\build_release.ps1
```

Artifacts:
- Setup EXE: `dist-installer\FFmpegConverter-Setup-<version>.exe`
- Portable ZIP: `dist-installer\FFmpegConverter-Portable-<version>.zip`

## 14) GitHub Publish / Release

EN:
- CI workflow: `.github/workflows/windows-release.yml`
- Triggers:
  - manual (`workflow_dispatch`)
  - tags like `v1.0.0`
- For an official release:
  1. Set version in `VERSION`.
  2. Commit and push.
  3. Create and push tag:
     ```powershell
     git tag v1.0.0
     git push origin v1.0.0
     ```
  4. Workflow builds EXE + Setup + ZIP and attaches artifacts to GitHub Release.

DE:
- CI-Workflow: `.github/workflows/windows-release.yml`
- Trigger:
  - manuell (`workflow_dispatch`)
  - Tags wie `v1.0.0`
- Für ein offizielles Release:
  1. Version in `VERSION` setzen.
  2. Commit und Push.
  3. Tag erstellen und pushen:
     ```powershell
     git tag v1.0.0
     git push origin v1.0.0
     ```
  4. Workflow baut EXE + Setup + ZIP und hängt Artefakte an das GitHub-Release.

## 15) Files / Dateien

- `main.py` - application
- `requirements.txt` - runtime dependencies
- `requirements-build.txt` - build dependencies
- `ffmpeg_konverter.spec` - PyInstaller spec
- `installer/FFmpegConverter.iss` - Inno Setup installer script
- `scripts/build_exe.ps1` - EXE build script
- `scripts/build_installer.ps1` - installer build script
- `scripts/build_release.ps1` - full release build script
- `scripts/test_installer.ps1` - automated installer smoke test (install + keep/delete user data)
- `.github/workflows/windows-release.yml` - GitHub Actions release workflow
- `LICENSE` - MIT license
- `THIRD_PARTY_NOTICES.md` - third-party licenses/links and notices
- `RELEASE_CHECKLIST.md` - practical release checklist
- `README.md` - this document

## 16) License / Lizenz

EN:
- This project is licensed under the MIT License. See `LICENSE`.
- Third-party components (e.g. FFmpeg/Qt) have their own license terms.
  See `THIRD_PARTY_NOTICES.md`.

DE:
- Dieses Projekt steht unter der MIT-Lizenz. Siehe `LICENSE`.
- Drittanbieter-Komponenten (z. B. FFmpeg/Qt) haben eigene Lizenzbedingungen.
  Siehe `THIRD_PARTY_NOTICES.md`.
