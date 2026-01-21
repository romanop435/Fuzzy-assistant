# Fazi Assistant (offline)

Offline Windows voice assistant with wake word, STT (Vosk), TTS (SAPI via pyttsx3), timers, math, and tray UI.

## Requirements

- Windows 10/11
- Python 3.10+
- Microphone
- Vosk Russian model (see below)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Download Vosk model

1) Download `vosk-model-small-ru-0.22` from https://alphacephei.com/vosk/models
2) Extract to `models\vosk-model-small-ru-0.22`
3) Or change `config/settings.yaml` -> `stt.model_path` to your model location.

## Run

```powershell
python -m app.main
```

## Build .exe

```powershell
pip install pyinstaller
.\build.ps1
```

Binary output: `dist\FaziAssistant.exe`
If `models\` exists, it is bundled into the build automatically.
If `assets\logo-fuzzy.png` exists, `build.ps1` generates `assets\logo-fuzzy.ico` and uses it as the .exe icon.

## Build installer

Installer uses Inno Setup.

1) Install Inno Setup: https://jrsoftware.org/isinfo.php
2) Build the exe first: `.\build.ps1`
3) Run:

```powershell
iscc installer\FaziAssistant.iss
```

Output: `dist-installer\FaziAssistantSetup.exe`

## Configs

All configs are in `config\`.

- `config\settings.yaml` - wake word, device, timeouts, TTS, UI theme.
- `config\commands.yaml` - command patterns and actions.
- `config\targets.yaml` - site aliases -> URL.
- `config\allowlist.yaml` - safe files/folders/apps that can be opened.

### Add new command

1) Add an entry in `config\commands.yaml`.
2) Use `{param}` placeholders in patterns to capture values.
3) Map to an `action.type`.
4) If the action type is new, add a handler in `app\core\actions.py`.

### Add site alias

Edit `config\targets.yaml`:

```yaml
aliases:
  github: "https://github.com"
```

### Allowlist (safe open/run)

Edit `config\allowlist.yaml`:

```yaml
items:
  - name: "notepad"
    path: "C:/Windows/System32/notepad.exe"
    type: "app"
    executable: true
```

Only allowlisted items can be opened by voice. For `.exe` you must set `executable: true`.

## Command list

The full command list (in Russian) lives in `config\commands.yaml` and can be extended there.

## Notes

- Wake word is stored in `config\settings.yaml` and may use `\uXXXX` escapes; `config\commands.yaml` and `config\targets.yaml` are UTF-8 with Russian phrases.
- If the tray is enabled, closing the window hides it to the tray. Use the Exit button to quit.
- Console debug output can be toggled via `config\settings.yaml` -> `stt.debug_console`.
- Listening starts automatically on launch (wake word mode). Use the "Commands without \"Fazi\"" toggle to accept commands without the wake word.
- Text typing uses Windows SendInput and only works in the currently focused window (won't type into elevated apps when Fazi is not elevated).
- Splash screen assets are configured in `config\settings.yaml` under `ui.splash_icon` and `ui.splash_sound`.
