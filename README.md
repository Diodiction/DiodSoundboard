# DiodSoundboard
A simple audio soundboard application built with Python

# Python Audio Mixer & Soundboard

A simple but powerful audio mixer and soundboard application built with Python. It's designed to mix your microphone input with various audio files and route the combined audio to a virtual audio device, making it perfect for streaming, gaming, or online calls.

This application runs in **Administrator Mode** to allow global hotkeys (hotkeys that work even when the app is minimized).

I have been using this on my main without any problems, but USE IT AT YOUR OWN RISK.

---
## 한국어 (Korean)

### 🎤 프로그램 설명

이 프로그램은 사용자의 마이크 입력과 오디오 파일을 실시간으로 믹스(Mix)하여 VB-Cable과 같은 가상 오디오 장치로 보내는 사운드보드 툴입니다.

프로그램이 최소화되어 있어도 핫키가 작동하도록 **관리자 권한**으로 실행됩니다.

모든 장치, 볼륨, 핫키 설정은 `config.json` 파일에 자동으로 저장되어, 프로그램을 다시 켜도 설정을 기억합니다.

### ✨ 주요 기능

* **마이크 & 오디오 믹싱:** 마이크 입력과 오디오 파일(`.mp3`, `.m4a`, `.wav` 등)을 믹스합니다.
* **파일별 개별 핫키:** 모든 오디오 파일에 `Alt+Ctrl+P`와 같은 조합키를 포함한 고유 핫키를 지정할 수 있습니다.
* **'선택 재생' 전역 핫키:** 리스트에서 현재 선택한 파일을 재생하는 별도의 핫키를 지원합니다.
* **로컬 모니터링:** 믹스(송출)와 동시에 사용자의 헤드폰으로도 재생되는 소리를 들을 수 있습니다. ("Preview Vol"로 조절)
* **설정 자동 저장:** 모든 장치, 볼륨, 핫키 설정이 자동으로 저장되고 로드됩니다.
* **자동 설치:** `setup.bat` 스크립트가 가상 환경 생성, 라이브러리 설치, **FFmpeg** 다운로드까지 모두 자동으로 처리합니다.

### 📋 요구 사항

* **운영체제:** **Windows 10 / 11** (`pycaw`, `pywin32`, `keyboard` 라이브러리 작동을 위해 필수).
* **Python:** **Python 3.7+** 버전이 설치되어 있어야 하며, 시스템 PATH에 추가되어 있어야 합니다.
* **가상 오디오 장치:** 가상 오디오 케이블이 설치되어 있어야 합니다.
    * **추천:** [VB-Audio Cable](https://vb-audio.com/Cable/) (무료).
* **인터넷 연결:** `setup.bat` 최초 실행 시 라이브러리와 FFmpeg를 다운로드하기 위해 필요합니다.

### 🚀 설치 및 사용법

1.  **VB-Cable 설치:** (아직 없다면) [VB-Audio Cable을 다운로드하여 설치](https://vb-audio.com/Cable/)합니다.
2.  **파일 다운로드:** 이 저장소의 모든 파일(`Soundboard.py`, `setup_soundboard.py`, `setup.bat`, `RUN.bat`)을 하나의 폴더에 다운로드합니다.
3.  **셋업 실행:** **`setup.bat`** 파일을 더블 클릭해 실행합니다.
    * `venv` 폴더가 생성되고, 필요한 모든 파이썬 라이브러리와 FFmpeg가 자동으로 설치됩니다.
    * `Soundboard Rsc` 폴더와 예제 파일도 함께 생성됩니다.
4.  **사운드 추가:** `Soundboard Rsc` 폴더 안에 원하는 오디오 파일(.mp3, .m4a 등)을 넣습니다.
5.  **프로그램 실행:** **`RUN.bat`** 파일을 더블 클릭해 프로그램을 실행합니다. (자동으로 관리자 권한을 요청합니다.)

#### 최초 프로그램 설정


1.  **`Mic In`:** 사용자의 **실제 마이크**를 선택합니다.
2.  **`Mix Out`:** 가상 오디오 장치(예: **`CABLE Input (VB-Audio...)`**)를 선택합니다.
3.  **`Start Mic` 클릭:** 버튼이 "Stop Mic"(빨간색)으로 바뀝니다. 이제 믹싱이 활성화되었습니다.
4.  **핫키 지정:** 파일 목록 우측의 'Set' 버튼을 눌러 핫키를 지정합니다. 핫키 캡처 창에서 **Esc** 키를 누르면 핫키가 해제됩니다.
5.  **출력 설정:** 디스코드, OBS 등 방송/채팅 프로그램의 "입력 장치"를 **`CABLE Output (VB-Audio...)`**으로 설정합니다.

------------------------------------------------------------------------------------------------------------------------------------------------
## English

### 🎤 Description

This program is a soundboard that mixes your live microphone audio with sound effects. The final mixed audio is sent to a virtual output device (like VB-Cable), while you can *also* hear the sound effects locally through your headphones.

It saves all your settings (devices, volumes, and hotkeys) to a `config.json` file, so all your preferences are loaded automatically every time you start it.

### ✨ Features

* **Mic + Audio Mixing:** Mixes your microphone with sound files (`.mp3`, `.m4a`, `.wav`, etc.).
* **Per-File Hotkeys:** Assign a unique hotkey (including combinations like `Alt+Ctrl+P`) to any sound file.
* **Global "Play Selected" Hotkey:** A separate hotkey to play the file you currently have selected in the list.
* **Local Monitoring:** You hear the sound effects you play (using the "Preview Vol") at the same time as they are sent to the mix.
* **Settings Persistence:** Automatically saves and loads all your device, volume, and hotkey settings.
* **Auto-Setup:** The setup script automatically creates a virtual environment, installs dependencies, and even downloads the correct version of **FFmpeg** for you.

### 📋 Requirements

* **OS:** **Windows 10 / 11**. (This is required for the `pycaw`, `pywin32`, and `keyboard` libraries to function correctly).
* **Python:** **Python 3.7+** must be installed and added to your system's PATH.
* **Virtual Audio Device:** You must have a virtual audio device installed.
    * **Recommended:** [VB-Audio Cable](https://vb-audio.com/Cable/) (free).
* **Internet Connection:** Required **one time** for `Setup.bat` to download libraries and FFmpeg.

### 🚀 Installation & Usage

1.  **Install VB-Cable:** If you haven't already, [download and install VB-Audio Cable](https://vb-audio.com/Cable/).
2.  **Download Files:** Download all files from this repository (`Soundboard.py`, `setup_soundboard.py`, `setup.bat`, `RUN.bat`) into a single folder.
3.  **Run Setup:** Double-click **`setup.bat`**.
    * This will create a `venv` folder, install all required Python libraries, and automatically download FFmpeg into `venv/ffmpeg_bin`.
    * It will also create a `Soundboard Rsc` folder with an example sound file.
4.  **Add Sounds:** Place your sound files (`.mp3`, `.m4a`, `.wav`, etc.) into the `Soundboard Rsc` folder.
5.  **Run the App:** Double-click **`RUN.bat`** to start the program. It will automatically request Administrator privileges.

#### First-Time App Setup


1.  **Mic In:** Select your **real microphone**.
2.  **Mix Out:** Select your virtual audio device (e.g., **`CABLE Input (VB-Audio...)`**).
3.  **Press `Start Mic`:** The button will turn red ("Stop Mic"). The stream is now active.
4.  **Set Hotkeys:** Click the "Set" button next to any file to assign a hotkey. Press **Escape** in the capture window to clear a hotkey.
5.  **Configure Output:** In your streaming/chat app (Discord, OBS), set your "Input Device" to be **`CABLE Output (VB-Audio...)`**.





---

### 🗂️ Project Files

* **`Soundboard.py`**: The main application logic, UI, and audio processing.
* **`setup_soundboard.py`**: The Python script that creates the venv, installs dependencies, and downloads FFmpeg.
* **`setup.bat`**: A batch file to run the `setup_soundboard.py` script using your system's Python.
* **`RUN.bat`**: A batch file that runs the main `Soundboard.py` application using the Python inside the `venv` folder.
