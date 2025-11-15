import customtkinter as ctk
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import sys
from tkinter import filedialog, messagebox
from functools import partial
import threading
import ctypes
import shutil 
import json 
import signal 
import time 

# --- Dependency Checks ---

try:
    import win32api 
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[!] 'pywin32' library not found. Settings may not save if console is closed.")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: 'pydub' library not found. Run 'pip install pydub'. MP3/M4A/OGG files cannot be loaded.")
except Exception as e:
    PYDUB_AVAILABLE = False
    print(f"Warning: Error loading 'pydub' (FFmpeg might be missing): {e}")

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("Warning: 'keyboard' library not found. Run 'pip install keyboard'. Hotkey features will be disabled.")

# --- FFmpeg Path Configuration (Must run before pydub import) ---
try:
    ffmpeg_dir = None
    # For PyInstaller .exe
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        script_dir = os.path.dirname(sys.executable)
        ffmpeg_dir = os.path.join(script_dir, "ffmpeg_bin")
    # For .py script
    else:
        project_root = os.path.dirname(os.path.abspath(__file__)) 
        ffmpeg_dir = os.path.join(project_root, "venv", "ffmpeg_bin")

    # Add venv FFmpeg path to environment PATH
    if ffmpeg_dir and os.path.isdir(ffmpeg_dir):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
        print(f"Added FFmpeg/ffprobe search path (venv): {ffmpeg_dir}")
    else:
        print(f"Note: '{ffmpeg_dir}' folder not found. (Did you run setup.bat?)")

    # Check if ffmpeg is now available on the system PATH
    ffmpeg_found = shutil.which("ffmpeg")
    ffprobe_found = shutil.which("ffprobe")

    if ffmpeg_found and ffprobe_found:
        print(f"FFmpeg found: {ffmpeg_found}")
        print(f"ffprobe found: {ffprobe_found}")
    else:
        print("Warning: ffmpeg.exe or ffprobe.exe not found in PATH.")
        print("         Please run 'setup.bat' to download FFmpeg.")
        if not ffmpeg_found: print("         (ffmpeg not found)")
        if not ffprobe_found: print("         (ffprobe not found)")
        print("         (MP3/M4A/OGG file loading may fail.)")
            
except Exception as e:
    print(f"Error during FFmpeg path setup: {e}")

# --- Helper Functions for Admin & Audio Devices ---

def is_admin():
    """Check if the script is running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Re-run the script with Administrator privileges."""
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1)
    except Exception as e:
        print(f"Failed to restart with admin rights: {e}")
        messagebox.showerror("Error", f"Failed to acquire Admin rights:\n{e}")

try:
    from pycaw.pycaw import AudioUtilities
    from comtypes import CoInitialize, CoUninitialize
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("Note: 'pycaw' not found. Run 'pip install pycaw' to hide disabled audio devices.")
except Exception as e:
    PYCAW_AVAILABLE = False
    print(f"Note: Error loading 'pycaw': {e}")

def get_active_windows_devices():
    """
    Uses pycaw to get a set of 'Active' (enabled) audio device names.
    Returns None if pycaw is unavailable or fails.
    """
    if not PYCAW_AVAILABLE:
        return None
    
    print("pycaw: Scanning for active audio devices...")
    active_devices_set = set()
    try:
        CoInitialize()
        devices = AudioUtilities.GetDevices() 
        for device in devices:
            if device.state() == 1: # 1 == DEVICE_STATE_ACTIVE
                active_devices_set.add(device.FriendlyName)
        print(f"pycaw: Found {len(active_devices_set)} active devices.")
        CoUninitialize()
        return active_devices_set
    except Exception as e:
        print(f"pycaw: Device scan failed (disabling filter). (Error: {e})")
        try: CoUninitialize()
        except Exception: pass
        return None

# --- Main Application Class ---

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudioMixerApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("🎧 Audio Mixer & Soundboard (Admin Mode)")
        self.geometry("700x850")

        # --- App State & Config ---
        self.config_file = "config.json"
        self.saved_mic_name = None
        self.saved_mix_out_name = None
        self.is_closing = False
        
        # --- Hotkey Modifier Definitions (Centralized) ---
        # 1. For capturing (tkinter keysym -> keyboard name)
        self.modifier_map = {
            'control_l': 'left ctrl',
            'control_r': 'right ctrl',
            'shift_l': 'left shift',
            'shift_r': 'right shift',
            'alt_l': 'left alt',
            'alt_r': 'right alt', 
            'alt_gr': 'alt gr',
            'super_l': 'left windows',
            'super_r': 'right windows',
            'app': 'apps'
        }
        # 2. For parsing (all known names for the keyboard lib)
        self.known_mods = set(self.modifier_map.values())
        self.known_mods.update(['ctrl', 'shift', 'alt', 'win'])

        # --- Audio Stream State ---
        self.stream = None
        self.is_mixing = False
        self.stream_samplerate = 44100
        self.stream_channels = 2

        # --- Audio Data Cache ---
        self.sound_cache = {}
        self.selected_sound_key = None

        # --- Audio Playback State (Thread-safe) ---
        self.music_data = None
        self.music_play_pos = 0
        self.music_lock = threading.Lock()
        
        self.music_request_lock = threading.Lock()
        self.music_request = None # (data, pos) tuple

        # --- Volume Settings ---
        self.mic_vol = 0.8
        self.music_vol = 0.5
        self.preview_vol = 0.7 # Used for Preview button AND local monitoring

        # --- Hotkey Storage ---
        self.current_hotkey = "6" # Default 'Play Selected' hotkey
        self.file_hotkeys = {}    # { "C:/.../beep.mp3": "ctrl+1", ... }
        self.file_hotkey_buttons = {} # { "C:/.../beep.mp3": <CTkButton_Widget>, ... }
        
        # Load settings from config.json (overwrites defaults)
        self.load_settings()

        # --- Hotkey Capture State ---
        self.capture_window = None 
        self.current_capture_type = None # "mix" or "file"
        self.current_capture_file_path = None
        self.captured_modifiers = set()
        self.captured_key = None
        
        # --- Hotkey Press-State Flags (for repeat prevention) ---
        self.mix_hotkey_down = False
        self.file_hotkey_down_flags = {}

        # --- Build UI ---
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # 2. Audio Device Frame
        device_frame = ctk.CTkFrame(main_frame)
        device_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        device_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(device_frame, text="🎤 Mic In:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.mic_in_dropdown = ctk.CTkOptionMenu(device_frame, values=["Loading..."], command=self.on_mic_device_change)
        self.mic_in_dropdown.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(device_frame, text="🔈 Mix Out:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.mix_out_dropdown = ctk.CTkOptionMenu(device_frame, values=["Loading..."], command=self.on_mix_out_device_change)
        self.mix_out_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self.mic_device_id = None
        self.mix_out_device_id = None

        # 3. File List Frame (dynamically populated)
        self.file_list_frame = ctk.CTkScrollableFrame(main_frame, label_text="Audio Files")
        self.file_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.file_buttons = [] # For managing selection highlights

        # 4. Volume Sliders Frame
        volume_frame = ctk.CTkFrame(main_frame)
        volume_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        volume_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(volume_frame, text="Mic Vol:").grid(row=0, column=0, padx=10, pady=5)
        self.mic_vol_slider = ctk.CTkSlider(volume_frame, from_=0.0, to=1.5, command=self.on_volume_change)
        self.mic_vol_slider.set(self.mic_vol)
        self.mic_vol_slider.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(volume_frame, text="Music Vol:").grid(row=1, column=0, padx=10, pady=5)
        self.music_vol_slider = ctk.CTkSlider(volume_frame, from_=0.0, to=1.5, command=self.on_volume_change)
        self.music_vol_slider.set(self.music_vol)
        self.music_vol_slider.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(volume_frame, text="Preview Vol:").grid(row=2, column=0, padx=10, pady=5)
        self.preview_vol_slider = ctk.CTkSlider(volume_frame, from_=0.0, to=1.5, command=self.on_volume_change)
        self.preview_vol_slider.set(self.preview_vol)
        self.preview_vol_slider.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # 5. Control Buttons Frame
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        control_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.preview_btn = ctk.CTkButton(control_frame, text="🔊 Preview Selected", command=lambda: self.preview_sound(source="GUI"), fg_color="#1f6AA5")
        self.preview_btn.grid(row=0, column=0, padx=5, pady=10)

        self.play_to_mix_btn = ctk.CTkButton(control_frame, text="🎶 Play Selected", command=self.play_to_mix_gui)
        self.play_to_mix_btn.grid(row=0, column=1, padx=5, pady=10)

        self.start_stop_btn = ctk.CTkButton(control_frame, text="🔴 Start Mic", command=self.toggle_mix,
                                            fg_color="#006400", hover_color="#008000")
        self.start_stop_btn.grid(row=0, column=2, padx=5, pady=10)

        # 6. Global Hotkey Frame
        hotkey_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        hotkey_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        hotkey_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hotkey_frame, text="Play Selected Hotkey:").grid(row=0, column=0, padx=(10,5), pady=5)
        self.hotkey_btn = ctk.CTkButton(hotkey_frame, text=f"Set ({self.current_hotkey})", 
                                        width=120, command=lambda: self.open_hotkey_capture_window("mix")) 
        self.hotkey_btn.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="ew")


        # --- App Initialization ---
        self.auto_load_files_from_rsc()
        self.load_audio_devices()

        # --- Window & Signal Handlers ---
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Catch console close (X button) or Ctrl+C
        if WIN32_AVAILABLE and os.name == 'nt':
            try:
                win32api.SetConsoleCtrlHandler(self.signal_handler, True)
                print("[*] Windows console close handler registered.")
            except Exception as e:
                print(f"[!] Failed to register console handler: {e}")
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            print("[*] Ctrl+C (SIGINT) handler registered.")
        except Exception as e:
            print(f"[!] Failed to register SIGINT handler: {e}")

        # Build and register all loaded hotkeys
        self.rebuild_all_hotkeys()

    # --- Hotkey System ---
    
    def _parse_hotkey(self, hotkey_str):
        """
        Parses a hotkey string like "ctrl+alt+6" into modifiers and a main key.
        Returns: (['ctrl', 'alt'], '6')
        """
        if not hotkey_str:
            return ([], "")
            
        parts = hotkey_str.lower().split('+')
        mods = []
        main_key = ""
        
        for part in parts:
            if part in self.known_mods:
                mods.append(part)
            else:
                main_key = part # Assumes last non-modifier is the main key
        
        return (mods, main_key)
    
    def rebuild_all_hotkeys(self):
        """
        Clears all system hotkeys and registers them again from storage.
        This is the central function for managing all hotkey bindings.
        """
        if not KEYBOARD_AVAILABLE:
            return
            
        print("[*] Rebuilding all hotkeys...")
        try:
            keyboard.unhook_all()
        except Exception as e:
            print(f"[!] unhook_all failed (ignoring): {e}")

        # 1. Register 'Play Selected' hotkey
        if self.current_hotkey:
            try:
                mods, main_key = self._parse_hotkey(self.current_hotkey)
                if main_key:
                    press_cb = partial(self.on_mix_key_press, required_mods=mods)
                    keyboard.on_press_key(main_key, press_cb)
                    keyboard.on_release_key(main_key, self.on_mix_key_release)
            except Exception as e:
                print(f"[!] Failed to register 'Play Selected' hotkey ('{self.current_hotkey}'): {e}")

        # 2. Register all individual 'File Hotkeys'
        for file_path, hotkey_str in self.file_hotkeys.items():
            if hotkey_str: # Only if hotkey is not empty
                try:
                    mods, main_key = self._parse_hotkey(hotkey_str)
                    if main_key:
                        press_cb = partial(self.on_file_key_press, 
                                           file_path=file_path, 
                                           required_mods=mods, 
                                           callback=partial(self.play_file_hotkey, file_path))
                        release_cb = partial(self.on_file_key_release, file_path=file_path)
                        
                        keyboard.on_press_key(main_key, press_cb)
                        keyboard.on_release_key(main_key, release_cb)
                except Exception as e:
                     print(f"[!] Failed to register file hotkey ('{hotkey_str}'): {e}")
    
    # --- 1. Audio Device Methods ---

    def load_audio_devices(self):
        """Loads audio devices, filtering out disabled ones if pycaw is available."""
        self.device_map = {}
        input_devices = ["(Mic Off)"]
        output_devices = ["(Default Speaker)"]

        active_devices_set = get_active_windows_devices()

        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis() 

            for i, device in enumerate(devices):
                # Filter out disabled WASAPI devices if possible
                if active_devices_set is not None:
                    try:
                        api_name = hostapis[device['hostapi']]['name']
                        sd_name = device['name']
                        if api_name == 'Windows WASAPI':
                            if sd_name not in active_devices_set:
                                print(f"Filtered (disabled/unplugged): {sd_name}")
                                continue 
                    except Exception as e:
                        print(f"Error during device filter (ignoring): {e}")
                
                device_name = f"({i}) {device['name']}"
                self.device_map[device_name] = i

                if device['max_input_channels'] > 0:
                    input_devices.append(device_name)
                if device['max_output_channels'] > 0:
                    output_devices.append(device_name)
            
            # Set dropdown values
            self.mic_in_dropdown.configure(values=input_devices)
            self.mix_out_dropdown.configure(values=output_devices)

            # Set Mic In (prioritize saved value)
            if self.saved_mic_name and self.saved_mic_name in input_devices:
                self.mic_in_dropdown.set(self.saved_mic_name)
            else:
                default_mic = next((d for d in input_devices if "Mic" in d and "CABLE" not in d), input_devices[0])
                self.mic_in_dropdown.set(default_mic)
            self.on_mic_device_change(self.mic_in_dropdown.get())

            # Set Mix Out (prioritize saved value)
            if self.saved_mix_out_name and self.saved_mix_out_name in output_devices:
                self.mix_out_dropdown.set(self.saved_mix_out_name)
            else:
                vb_cable_out = next((d for d in output_devices if "CABLE Input" in d), output_devices[0])
                self.mix_out_dropdown.set(vb_cable_out)
            self.on_mix_out_device_change(self.mix_out_dropdown.get())

        except Exception as e:
            messagebox.showerror("Audio Device Error", f"Failed to load audio devices: {e}")

    def on_mic_device_change(self, device_name):
        if device_name == "(Mic Off)":
            self.mic_device_id = None
        else:
            self.mic_device_id = self.device_map.get(device_name)
        print(f"Mic In ID set: {self.mic_device_id}")

    def on_mix_out_device_change(self, device_name):
        if device_name == "(Default Speaker)":
            self.mix_out_device_id = None # None = default device
        else:
            self.mix_out_device_id = self.device_map.get(device_name)
        print(f"Mix Out ID set: {self.mix_out_device_id}")

    # --- 2. File Loading & UI Methods ---

    def auto_load_files_from_rsc(self):
        """Finds all audio files, loads them into cache, and builds the file list UI."""
        try:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                script_dir = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
            
            rsc_folder = os.path.join(script_dir, "Soundboard Rsc")

            if not os.path.isdir(rsc_folder):
                print(f"Warning: 'Soundboard Rsc' folder not found at {rsc_folder}")
                messagebox.showwarning("Folder Not Found",
                                    f"'Soundboard Rsc' folder not found.\n\n{rsc_folder}\n\nPlease create it and add audio files.")
                return

            # Clear all existing UI and cache
            for widget in self.file_list_frame.winfo_children():
                widget.destroy()
            self.file_buttons.clear()
            self.sound_cache.clear()
            self.file_hotkey_buttons.clear()
            self.file_hotkey_down_flags.clear()
            self.selected_sound_key = None

            valid_extensions = ('.wav', '.flac', '.ogg', '.mp3', '.m4a')
            print(f"Loading files from '{rsc_folder}'...")
            loaded_files = 0
            
            for filename in os.listdir(rsc_folder):
                if filename.lower().endswith(valid_extensions):
                    full_path = os.path.join(rsc_folder, filename)
                    try:
                        # Load via pydub (for mp3/m4a/ogg) or soundfile (for wav/flac)
                        if PYDUB_AVAILABLE and (filename.lower().endswith(('.mp3', '.ogg', '.m4a'))):
                            sound = AudioSegment.from_file(full_path)
                        elif filename.lower().endswith(('.wav', '.flac')):
                            data, sr = sf.read(full_path, dtype='int16') 
                            if data.ndim == 1: # Convert mono to stereo
                                data = np.column_stack((data, data))
                            sound = AudioSegment(data.tobytes(), frame_rate=sr, sample_width=data.dtype.itemsize, channels=data.shape[1])
                        else:
                            if not PYDUB_AVAILABLE:
                                print(f"File skipped (pydub/ffmpeg required): {filename}")
                            continue

                        # Standardize audio format for mixing
                        sound = sound.set_frame_rate(self.stream_samplerate)
                        sound = sound.set_channels(self.stream_channels)
                        sound = sound.set_sample_width(2) # 16-bit

                        # Convert to numpy float32 array and cache
                        samples = np.array(sound.get_array_of_samples(), dtype=np.float32)
                        samples /= 32767.0 # Normalize to -1.0 to 1.0
                        samples = samples.reshape(-1, self.stream_channels)
                        self.sound_cache[full_path] = (samples, self.stream_samplerate)

                        # --- Create UI entry for the file ---
                        file_entry_frame = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
                        file_entry_frame.pack(fill="x", pady=2)
                        file_entry_frame.grid_columnconfigure(0, weight=1)

                        # File name button (for selecting)
                        btn = ctk.CTkButton(file_entry_frame, text=filename, fg_color="transparent", anchor="w")
                        btn.configure(command=partial(self.select_file, full_path, btn))
                        btn.bind("<Double-Button-1>", partial(self.on_file_double_click, full_path, btn))
                        btn.grid(row=0, column=0, sticky="ew", padx=(5, 5))

                        # Hotkey set button
                        hotkey_btn_text = "Set (None)"
                        if full_path in self.file_hotkeys:
                            hotkey_str = self.file_hotkeys.get(full_path)
                            if hotkey_str: 
                                hotkey_btn_text = f"Set ({hotkey_str})"
                        
                        hotkey_btn = ctk.CTkButton(file_entry_frame, text=hotkey_btn_text, width=120,
                                                   command=partial(self.open_hotkey_capture_window, "file", full_path))
                        hotkey_btn.grid(row=0, column=1, sticky="e", padx=(0, 5))

                        self.file_buttons.append(btn)
                        self.file_hotkey_buttons[full_path] = hotkey_btn
                        self.file_hotkey_down_flags[full_path] = False # Initialize press-state flag
                        loaded_files += 1

                    except Exception as e:
                        print(f"Failed to load file: {filename}, Error: {e}")

            print(f"Load complete: {loaded_files} files.")

        except Exception as e:
            print(f"Critical error during file auto-load: {e}")
            messagebox.showerror("Auto-Load Error", f"A critical error occurred: {e}")

    def select_file(self, file_path, selected_button):
        """Highlights the selected file in the UI."""
        self.selected_sound_key = file_path
        theme_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        for btn in self.file_buttons:
            btn.configure(fg_color="transparent")
        selected_button.configure(fg_color=theme_color)

    def on_file_double_click(self, file_path, button, event):
        """Selects and previews a file on double-click."""
        print(f"Double-click: {file_path}")
        self.select_file(file_path, button)
        self.preview_sound(source="GUI")

    # --- 3. Audio Playback Methods ---

    def on_volume_change(self, value):
        """Updates volume variables when sliders are moved."""
        self.mic_vol = self.mic_vol_slider.get()
        self.music_vol = self.music_vol_slider.get()
        self.preview_vol = self.preview_vol_slider.get()

    def preview_sound(self, source="GUI"):
        """Plays the *currently selected* sound to the *default speaker*."""
        if not self.selected_sound_key:
            if source == "GUI":
                messagebox.showwarning("No File Selected", "Please select a file to preview.")
            return

        try:
            data, sr = self.sound_cache[self.selected_sound_key]
            preview_data = data * self.preview_vol
            np.clip(preview_data, -1.0, 1.0, out=preview_data)

            print(f"🔊 PREVIEW ({source}): {os.path.basename(self.selected_sound_key)} (Vol: {self.preview_vol:.2f})")
            sd.play(preview_data, sr, device=None, blocking=False)
        except Exception as e:
            if source == "GUI":
                messagebox.showerror("Playback Error", f"Error during preview: {e}")
            else:
                print(f"[Hotkey] Playback Error: {e}")

    def _internal_play_to_mix_by_path(self, file_path, source="GUI"):
        """
        [Core Logic] Plays a sound (by path) to both:
        1. Local Monitor (Default Speaker)
        2. Mix Out (VB-Cable)
        """
        if not self.is_mixing:
            if source == "GUI":
                messagebox.showwarning("Stream Not Started", "Please press 'Start Mic' to begin mixing.")
            else:
                print(f"[HOTKEY ({source})] Mix stream is not running.")
            return

        if not file_path or file_path not in self.sound_cache:
            if source == "GUI":
                messagebox.showwarning("No File Selected", "Please select a file to play.")
            else:
                print(f"[HOTKEY ({source})] Sound file not selected or not in cache.")
            return

        try:
            data, sr = self.sound_cache[file_path]
            if sr != self.stream_samplerate:
                print(f"Warning: Sample rate mismatch! {sr} != {self.stream_samplerate} (skipping)")
                return
        except Exception as e:
            print(f"[!] Sound cache load error: {e}")
            return

        # 1. Play to Local Monitor (uses 'Preview Vol')
        try:
            monitor_data = data * self.preview_vol
            np.clip(monitor_data, -1.0, 1.0, out=monitor_data)
            sd.play(monitor_data, sr, device=None, blocking=False) 
        except Exception as e:
            print(f"[!] Local monitoring playback failed: {e}")

        # 2. Send to Mix Out (via thread-safe request)
        with self.music_request_lock:
            print(f"🎶 PLAY TO MIX ({source}): {os.path.basename(file_path)}")
            self.music_request = (data, 0) # Set (data, position)

    def _internal_play_to_mix(self, source="GUI"):
        """Wrapper to play the *currently selected* file."""
        self._internal_play_to_mix_by_path(self.selected_sound_key, source)

    def play_to_mix_gui(self):
        """Called by 'Play Selected' GUI button."""
        self._internal_play_to_mix(source="GUI")

    def play_to_mix_hotkey(self):
        """Called by 'Play Selected' global hotkey."""
        self._internal_play_to_mix(source="Hotkey")
        
    def play_file_hotkey(self, file_path):
        """Called by an individual file's hotkey."""
        self._internal_play_to_mix_by_path(file_path, source="File Hotkey")

    # --- 4. Hotkey Registration & Capture ---

    def register_file_hotkey(self, file_path, new_hotkey_str, initial=False):
        """Sets a hotkey for a specific file and rebuilds all hotkeys."""
        if not KEYBOARD_AVAILABLE:
            if not initial:
                messagebox.showwarning("Keyboard Library Missing", "'keyboard' library is not installed.")
            return
        
        hotkey_to_set = new_hotkey_str.strip().lower() if new_hotkey_str else ""

        # Check for duplicates
        if hotkey_to_set:
            if hotkey_to_set == self.current_hotkey:
                print(f"Hotkey Error: '{hotkey_to_set}' is already used by 'Play Selected'.")
                if not initial:
                    messagebox.showerror("Duplicate Hotkey", f"'{hotkey_to_set}' is already used by 'Play Selected'.")
                return 

            for path, hotkey in self.file_hotkeys.items():
                if path != file_path and hotkey == hotkey_to_set:
                    print(f"Hotkey Error: '{hotkey_to_set}' is already assigned to another file.")
                    if not initial:
                        messagebox.showerror("Duplicate Hotkey", f"'{hotkey_to_set}' is already assigned to '{os.path.basename(path)}'.")
                    return

        # Store the new hotkey
        self.file_hotkeys[file_path] = hotkey_to_set
        
        # Update UI
        if file_path in self.file_hotkey_buttons:
            if not hotkey_to_set:
                self.file_hotkey_buttons[file_path].configure(text="Set (None)")
            else:
                self.file_hotkey_buttons[file_path].configure(text=f"Set ({hotkey_to_set})")

        if not initial:
            if hotkey_to_set:
                print(f"File hotkey set: '{hotkey_to_set}' for {os.path.basename(file_path)}")
                messagebox.showinfo("Hotkey Set", f"Hotkey '{hotkey_to_set}' was set.")
            else:
                print(f"File hotkey cleared: {os.path.basename(file_path)}")
        
        # Re-register all hotkeys
        self.rebuild_all_hotkeys()

    def register_hotkey(self, new_hotkey=None, initial=False):
        """Sets the global 'Play Selected' hotkey and rebuilds all hotkeys."""
        if not KEYBOARD_AVAILABLE:
            if not initial:
                messagebox.showwarning("Keyboard Library Missing", "'keyboard' library is not installed.")
            return
        
        hotkey_to_set = self.current_hotkey
        if new_hotkey is not None:
            hotkey_to_set = new_hotkey.strip().lower()

        # Check for duplicates
        if hotkey_to_set and hotkey_to_set in self.file_hotkeys.values():
            print(f"Hotkey Error: '{hotkey_to_set}' is already assigned to a file.")
            if not initial:
                messagebox.showerror("Duplicate Hotkey", f"Hotkey '{hotkey_to_set}' is already assigned to a file.")
            return

        self.current_hotkey = hotkey_to_set
        
        if not hotkey_to_set:
            self.hotkey_btn.configure(text="Set (None)")
        else:
            self.hotkey_btn.configure(text=f"Set ({hotkey_to_set})")
            
        if not initial:
            if hotkey_to_set:
                print(f"Global hotkey set: '{hotkey_to_set}'")
                messagebox.showinfo("Hotkey Set", f"Hotkey '{hotkey_to_set}' was set.")
            else:
                print("Global hotkey cleared.")

        self.rebuild_all_hotkeys()
        
    def open_hotkey_capture_window(self, hotkey_type, file_path=None):
        """Opens the modal popup window to capture a new hotkey."""
        if not KEYBOARD_AVAILABLE:
            messagebox.showwarning("Keyboard Library Missing", "'keyboard' library is not installed.")
            return

        if self.capture_window and self.capture_window.winfo_exists():
            self.capture_window.focus()
            return
        
        self.current_capture_type = hotkey_type
        self.current_capture_file_path = file_path
        
        # Disable the button that was clicked
        if hotkey_type == "mix":
            self.hotkey_btn.configure(state="disabled", text="Recording...")
        elif hotkey_type == "file":
            if file_path and file_path in self.file_hotkey_buttons:
                self.file_hotkey_buttons[file_path].configure(state="disabled", text="Recording...")
            else:
                print(f"Error: Could not find button for file: {file_path}")
                return
        
        # Create Toplevel window
        self.capture_window = ctk.CTkToplevel(self)
        self.capture_window.title("Set Hotkey")
        self.capture_window.geometry("300x120")
        self.capture_window.attributes("-topmost", True)
        
        self.capture_label = ctk.CTkLabel(self.capture_window, text="Press desired hotkey...\n(Press 'Escape' to clear)",
                                          font=ctk.CTkFont(size=14))
        self.capture_label.pack(pady=20, fill="both", expand=True)
        
        self.capture_window.grab_set() 
        self.capture_window.protocol("WM_DELETE_WINDOW", self.cancel_hotkey_capture)
        
        # Reset capture state and bind events
        self.captured_modifiers = set()
        self.captured_key = None
        self.capture_window.bind("<KeyPress>", self.on_key_press_capture)
        self.capture_window.bind("<KeyRelease>", self.on_key_release_capture)
        self.capture_window.focus_force() 

    def on_key_press_capture(self, event):
        """Handles key *press* events in the capture window."""
        keysym = event.keysym.lower()
        
        # 'Escape' key clears the hotkey
        if keysym == 'escape':
            print("Hotkey clear signal (Escape) detected.")
            if self.current_capture_type == "mix":
                self.register_hotkey(new_hotkey="")
            elif self.current_capture_type == "file":
                self.register_file_hotkey(self.current_capture_file_path, new_hotkey_str="")
            
            self.cancel_hotkey_capture(from_finalize=True)
            return

        # Check if it's a modifier key
        if keysym in self.modifier_map:
            self.captured_modifiers.add(self.modifier_map[keysym])
            self.update_capture_label()
            return 

        # It's a main key; capture it (only once)
        if self.captured_key:
            return
            
        # This is the line that had a syntax error (missing ':')
        if keysym in self.modifier_map:
            return 
            
        self.captured_key = keysym
        self.update_capture_label()

    def on_key_release_capture(self, event):
        """Handles key *release* events in the capture window."""
        
        # If the main key was released, finalize the capture
        if self.captured_key and event.keysym.lower() == self.captured_key:
            self.finalize_hotkey_capture()
        else:
            # Check if a modifier was released
            keysym = event.keysym.lower()
            
            # Use self.modifier_map (this was a bug, used a local map before)
            if keysym in self.modifier_map:
                key_name = self.modifier_map[keysym]
                if key_name in self.captured_modifiers:
                    self.captured_modifiers.remove(key_name)
                    self.update_capture_label()

    def update_capture_label(self):
        """Updates the text label in the capture window."""
        if not (self.capture_window and self.capture_window.winfo_exists()):
            return
        
        mods = " + ".join(self.captured_modifiers)
        key = self.captured_key or "..."
        display_text = f"{mods} + {key}" if mods else key
        self.capture_label.configure(text=display_text)

    def finalize_hotkey_capture(self):
        """Builds the hotkey string and calls the registration function."""
        if not (self.capture_window and self.capture_window.winfo_exists()):
            return
            
        mods_list = list(self.captured_modifiers)

        if self.captured_key:
            # Build the string (e.g., "left ctrl+alt+6")
            new_hotkey_str = "+".join(mods_list + [self.captured_key])

            if self.current_capture_type == "mix":
                self.register_hotkey(new_hotkey=new_hotkey_str)
            elif self.current_capture_type == "file":
                self.register_file_hotkey(self.current_capture_file_path, new_hotkey_str)
        else:
            print("No main key was captured.")

        self.cancel_hotkey_capture(from_finalize=True)

    def cancel_hotkey_capture(self, from_finalize=False):
        """Closes the capture window and re-enables the UI button."""
        if self.capture_window and self.capture_window.winfo_exists():
            self.capture_window.grab_release()
            self.capture_window.destroy()
            self.capture_window = None
        
        # Restore the button's original state and text
        if self.current_capture_type == "mix":
            hotkey_str = self.current_hotkey or "None"
            self.hotkey_btn.configure(state="normal", text=f"Set ({hotkey_str})")
        
        elif self.current_capture_type == "file":
            file_path = self.current_capture_file_path
            if file_path and file_path in self.file_hotkey_buttons:
                hotkey_str = self.file_hotkeys.get(file_path, "None")
                if not hotkey_str: hotkey_str = "None"
                self.file_hotkey_buttons[file_path].configure(state="normal", text=f"Set ({hotkey_str})")
        
        self.current_capture_type = None
        self.current_capture_file_path = None
        
        if not from_finalize:
            print("Hotkey setup cancelled.")
            
    # --- Hotkey Press/Release Handlers (for repeat prevention) ---
    
    def on_mix_key_press(self, keyboard_event, required_mods):
        """'Play Selected' hotkey *press* handler."""
        if self.mix_hotkey_down:
            return # Key is already held down
        
        # Check if all required modifier keys are also pressed
        for mod in required_mods:
            if not keyboard.is_pressed(mod):
                return # Required modifier not pressed
        
        self.mix_hotkey_down = True
        self.play_to_mix_hotkey()

    def on_mix_key_release(self, keyboard_event):
        """'Play Selected' hotkey *release* handler."""
        self.mix_hotkey_down = False

    def on_file_key_press(self, keyboard_event, file_path, required_mods, callback):
        """Individual file hotkey *press* handler."""
        if self.file_hotkey_down_flags.get(file_path, False):
            return # Key is already held down
        
        for mod in required_mods:
            if not keyboard.is_pressed(mod):
                return # Required modifier not pressed
        
        self.file_hotkey_down_flags[file_path] = True
        callback() 

    def on_file_key_release(self, keyboard_event, file_path):
        """Individual file hotkey *release* handler."""
        if file_path in self.file_hotkey_down_flags:
            self.file_hotkey_down_flags[file_path] = False

    # --- 5. Audio Stream Control ---
    
    def toggle_mix(self):
        """Starts or stops the main audio mixing stream."""
        if self.is_mixing:
            self.is_mixing = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            with self.music_lock:
                self.music_data = None
            self.start_stop_btn.configure(text="🔴 Start Mic", fg_color="#006400", hover_color="#008000")
            print("⏹️ MIX STREAM STOPPED")
        else:
            if self.mix_out_device_id is None:
                messagebox.showwarning("Device Not Selected", "A 'Mix Out' device (e.g., VB-Cable) must be selected.")
                return
            try:
                # Determine input device settings
                input_channels = 0
                input_device = None
                if self.mic_device_id is not None:
                    in_device_info = sd.query_devices(self.mic_device_id)
                    input_channels = in_device_info['max_input_channels']
                    input_device = self.mic_device_id
                    if input_channels == 0:
                        raise Exception(f"Selected mic '{in_device_info['name']}' has 0 input channels.")
                    print(f"Audio Stream: Mic detected ({input_channels}ch).")
                else:
                    print("Audio Stream: Mic OFF.")
                    input_channels = 0
                    input_device = None

                # Determine output device settings
                output_channels = 2 # Force stereo output
                self.stream_channels = output_channels
                output_device = self.mix_out_device_id

                print(f"Attempting stream: In={input_device}({input_channels}ch), Out={output_device}({output_channels}ch)")

                self.stream = sd.Stream(
                    device=(input_device, output_device),
                    samplerate=self.stream_samplerate,
                    channels=(input_channels, output_channels),
                    callback=self.audio_callback,
                    dtype='float32'
                )
                
                self.stream.start()
                self.is_mixing = True
                self.start_stop_btn.configure(text="⏹️ Stop Mic", fg_color="#8B0000", hover_color="#B22222")
                print(f"▶️ MIX STREAM STARTED (Mic: {self.mic_device_id} -> Out: {self.mix_out_device_id})")
                
            except Exception as e:
                messagebox.showerror("Stream Error", f"Failed to start audio stream: {e}\n\nCheck if devices support 44100Hz or if the correct devices are selected.")

    def audio_callback(self, indata, outdata, frames, time, status):
        """
        High-priority audio thread.
        This function MUST complete very quickly to avoid audio glitches.
        """
        if status:
            print(status, file=sys.stderr)
        
        outdata[:] = 0.0 # Clear output buffer
        
        # 1. Check for a new sound effect request from the main thread
        with self.music_request_lock:
            if self.music_request is not None:
                # If new request, transfer it to the main playback variables
                with self.music_lock: 
                    self.music_data, self.music_play_pos = self.music_request
                self.music_request = None
        
        # 2. Mix in microphone data (if active)
        if self.mic_device_id is not None and indata.shape[0] > 0:
            mic_chunk = indata * self.mic_vol
            in_channels = indata.shape[1]
            out_channels = outdata.shape[1]
            
            # Handle channel mapping (mono->stereo, etc.)
            if in_channels == 1 and out_channels == 2:
                mic_chunk = np.column_stack((mic_chunk, mic_chunk))
            elif in_channels == 2 and out_channels == 1:
                mic_chunk = np.mean(mic_chunk, axis=1, keepdims=True)
            elif in_channels > 2 and out_channels == 2:
                mic_chunk = mic_chunk[:, :2]
            elif in_channels != out_channels: 
                if out_channels == 2:
                    mic_chunk = np.column_stack((indata[:, 0], indata[:, 0])) * self.mic_vol
                else:
                    mic_chunk = indata[:, 0].reshape(-1, 1) * self.mic_vol

            # Add mic data to output
            if mic_chunk.shape[1] == out_channels:
                valid_frames = min(outdata.shape[0], mic_chunk.shape[0])
                outdata[:valid_frames] = mic_chunk[:valid_frames]
            
        # 3. Mix in sound effect data (if playing)
        with self.music_lock:
            if self.music_data is not None:
                chunk_size = frames
                remaining = len(self.music_data) - self.music_play_pos
                
                if remaining > 0:
                    play_size = min(chunk_size, remaining)
                    music_chunk = self.music_data[self.music_play_pos : self.music_play_pos + play_size]
                    outdata[:play_size] += (music_chunk * self.music_vol)
                    self.music_play_pos += play_size
                else:
                    self.music_data = None
                    self.music_play_pos = 0

        # Clip final output to prevent audio artifacts
        np.clip(outdata, -1.0, 1.0, out=outdata)

    # --- 6. App Shutdown & Settings ---
    
    def signal_handler(self, sig, frame=None):
        """Catches console close signals to trigger a safe shutdown."""
        print(f"[*] Exit signal (type={sig}) detected! Saving and closing...")
        self.on_close()
        if os.name == 'nt' and sig in (0, 2):
             return True
        return

    def on_close(self):
        """Handles GUI close event (X button) for safe shutdown."""
        if self.is_closing:
            return
        self.is_closing = True
        print("[*] on_close() called. Saving settings and shutting down...")
        
        self.save_settings()
        
        if self.is_mixing and self.stream:
            self.stream.stop()
            self.stream.close()
        
        if KEYBOARD_AVAILABLE:
            # All hotkeys are unhooked by rebuild_all_hotkeys on next launch
            pass 
                
        self.destroy()

    def load_settings(self):
        """Loads app settings from config.json."""
        if not os.path.exists(self.config_file):
            print(f"[*] {self.config_file} not found. Starting with default settings.")
            return

        print(f"[*] Loading settings from {self.config_file}...")
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Use .get() to safely load, falling back to defaults
            self.mic_vol = settings.get("mic_vol", self.mic_vol)
            self.music_vol = settings.get("music_vol", self.music_vol)
            self.preview_vol = settings.get("preview_vol", self.preview_vol)
            self.current_hotkey = settings.get("mix_hotkey", self.current_hotkey)
            self.file_hotkeys = settings.get("file_hotkeys", {})

            # Device names are loaded temporarily; applied after devices are listed
            self.saved_mic_name = settings.get("mic_device_name")
            self.saved_mix_out_name = settings.get("mix_out_device_name")
            
            print("[*] Settings loaded successfully.")
        except Exception as e:
            print(f"[!] Failed to load settings (file may be corrupt): {e}")
            print("[*] Using default settings.")

    def save_settings(self):
        """Saves current app settings to config.json."""
        print(f"[*] Saving settings to {self.config_file}...")
        settings = {
            "mic_device_name": self.mic_in_dropdown.get(),
            "mix_out_device_name": self.mix_out_dropdown.get(),
            
            "mic_vol": self.mic_vol_slider.get(),
            "music_vol": self.music_vol_slider.get(),
            "preview_vol": self.preview_vol_slider.get(),
            
            "mix_hotkey": self.current_hotkey,
            "file_hotkeys": self.file_hotkeys
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            print("[*] Settings saved.")
        except Exception as e:
            print(f"[!] Failed to save settings: {e}")


# --- Application Entry Point ---
if __name__ == "__main__":
    if is_admin():
        if KEYBOARD_AVAILABLE:
            print("---")
            print("Notification: Running with Administrator privileges.")
            print("Global hotkeys will work correctly.")
            print("---")
        
        app = AudioMixerApp()
        app.mainloop()
    else:
        print("Administrator rights required. Attempting to restart as admin...")
        run_as_admin()