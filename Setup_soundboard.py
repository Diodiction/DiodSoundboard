import os
import sys
import subprocess
import urllib.request
import zipfile # (신규) 압축 해제를 위해 임포트
import shutil  # (신규) 파일/폴더 관리를 위해 임포트

VENV_DIR = "venv"
REQUIREMENTS = "requirements.txt"
RSC_DIR_NAME = "Soundboard Rsc"

# 현재 시스템의 python.exe 경로
PYTHON_EXE = sys.executable

print(f"[*] Using Python executable: {PYTHON_EXE}")

# 1. 가상 환경(venv)이 없으면 생성
if not os.path.isdir(VENV_DIR):
    print(f"[*] Creating virtual environment at: .\\{VENV_DIR}")
    try:
        subprocess.check_call([PYTHON_EXE, "-m", "venv", VENV_DIR])
    except Exception as e:
        print(f"\n[!] FAILED to create virtual environment: {e}")
        print("[!] Check if Python 'venv' module is installed,")
        print("[!] or if you have write permissions in this folder.")
        input("Press Enter to exit...")
        sys.exit(1)
else:
    print(f"[*] Virtual environment '{VENV_DIR}' already exists.")

# 2. 가상 환경 내부의 python.exe 경로 설정
if os.name == "nt":  # Windows
    venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:  # macOS/Linux
    venv_python = os.path.join(VENV_DIR, "bin", "python")

# 3. venv 내부의 pip 업그레이드
try:
    print("[*] Upgrading pip inside venv...")
    subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
except Exception as e:
    print(f"\n[!] FAILED to upgrade pip: {e}")
    input("Press Enter to exit...")
    sys.exit(1)


# 4. requirements.txt 또는 기본 패키지 설치
print("[*] Installing dependencies...")
try:
    if os.path.isfile(REQUIREMENTS):
        print(f"[*] Installing from {REQUIREMENTS}...")
        subprocess.check_call([venv_python, "-m", "pip", "install", "-r", REQUIREMENTS])
    else:
        print(f"[*] {REQUIREMENTS} not found. Installing default soundboard packages...")
        
        # --- (수정) 'ffdl' 패키지 제거 ---
        base_packages = [
            "customtkinter",
            "sounddevice",
            "soundfile",
            "numpy",
            "pydub",
            "keyboard"
        ]
        print(f"[*] Installing base packages: {base_packages}")
        subprocess.check_call([venv_python, "-m", "pip", "install"] + base_packages)

        # Windows 전용 패키지
        if os.name == 'nt':
            print("[*] Installing Windows-specific package: pycaw")
            subprocess.check_call([venv_python, "-m", "pip", "install", "pycaw"])
            print("[*] Installing Windows-specific package: pywin32")
            subprocess.check_call([venv_python, "-m", "pip", "install", "pywin32"])
        else:
            print("[*] Skipping Windows-specific packages (pycaw, pywin32).")
            
except Exception as e:
    print(f"\n[!] FAILED to install packages: {e}")
    print("[!] Check your internet connection or pip logs.")
    input("Press Enter to exit...")
    sys.exit(1)

# --- (대대적 수정) 5. 'ffdl' 대신 FFmpeg 직접 다운로드 및 압축 해제 ---
print("\n[*] Checking for FFmpeg...")
try:
    ffmpeg_bin_dir = os.path.join(VENV_DIR, "ffmpeg_bin")
    ffmpeg_exe_path = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
    ffprobe_exe_path = os.path.join(ffmpeg_bin_dir, "ffprobe.exe")

    if not (os.path.exists(ffmpeg_exe_path) and os.path.exists(ffprobe_exe_path)):
        print(f"[*] FFmpeg not found. Downloading to '{ffmpeg_bin_dir}'...")
        os.makedirs(ffmpeg_bin_dir, exist_ok=True)
        
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        ffmpeg_zip_path = os.path.join(VENV_DIR, "ffmpeg-essentials.zip")

        # 1. 다운로드
        print(f"[*] Downloading: {ffmpeg_url}")
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip_path)
        print("[*] Download complete.")

        # 2. 압축 해제 (수정된 부분)
        print(f"[*] Extracting ffmpeg.exe and ffprobe.exe from {ffmpeg_zip_path}...")
        
        # --- (수정) zip_ref.open()을 'with' 구문으로 감싸서 핸들을 즉시 닫습니다 ---
        with zipfile.ZipFile(ffmpeg_zip_path, 'r') as zip_ref:
            found_ffmpeg = False
            found_ffprobe = False
            
            for file_path in zip_ref.namelist():
                filename = os.path.basename(file_path)
                
                if filename == 'ffmpeg.exe':
                    # (수정) source를 with 구문으로 열기
                    with zip_ref.open(file_path) as source:
                        with open(ffmpeg_exe_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                    found_ffmpeg = True
                    
                elif filename == 'ffprobe.exe':
                    # (수정) source를 with 구문으로 열기
                    with zip_ref.open(file_path) as source:
                        with open(ffprobe_exe_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                    found_ffprobe = True
                
                if found_ffmpeg and found_ffprobe:
                    break
            
            if not (found_ffmpeg and found_ffprobe):
                raise Exception("Could not find ffmpeg.exe/ffprobe.exe in the downloaded zip.")
        # --- 'with zipfile.ZipFile' 블록이 여기서 종료되며 파일 핸들을 모두 해제합니다 ---

        # 3. 임시 .zip 파일 삭제
        print("[*] Cleaning up temporary zip file...")
        os.remove(ffmpeg_zip_path) # 이제 정상적으로 삭제됩니다.
        print("[*] FFmpeg setup complete.")
        
    else:
        print(f"[*] FFmpeg already exists in '{ffmpeg_bin_dir}'. Skipping download.")

except Exception as e:
    print(f"\n[!] FAILED to download or extract FFmpeg: {e}")
    print("[!] Check your internet connection or file permissions.")
    input("Press Enter to exit...")
    sys.exit(1)
# --- 수정 끝 ---

# 6. 'Soundboard Rsc' 폴더 및 예제 파일 생성 (기존 코드와 동일)
print("\n[*] Checking for Soundboard Resource folder...")
try:
    rsc_dir_path = RSC_DIR_NAME
    
    if not os.path.isdir(rsc_dir_path):
        print(f"[*] Creating resource folder: {rsc_dir_path}")
        os.makedirs(rsc_dir_path, exist_ok=True)
    else:
        print(f"[*] Resource folder '{rsc_dir_path}' already exists.")

    example_file_name = "example_beep.mp3"
    example_file_path = os.path.join(rsc_dir_path, example_file_name)
    example_file_url = "https://www.soundjay.com/buttons/beep-07a.mp3" 

    if not os.path.isfile(example_file_path):
        print(f"[*] Downloading example sound ('{example_file_name}')...")
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(example_file_url, example_file_path)
        print("[*] Example sound downloaded successfully.")
    else:
        print(f"[*] Example sound '{example_file_name}' already exists.")

except Exception as e:
    print(f"\n[!] FAILED to create resource folder or download example file: {e}")
    print("[!] Check folder permissions or internet connection.")

print("\n[+] Done! Setup complete.")
print(f"[+] You can now run the soundboard using 'run_soundboard.bat'.")