import cv2
import numpy as np
import pyautogui as pygui
import pygetwindow as gw
import os
from datetime import datetime
import mss
import threading
import subprocess
import sys

# Global variables
paused = False
out = None
output_path = ""
x = y = width = height = 0
webcam_frame = None
webcam_running = False
use_webcam = False
use_microphone = False
mic_process = None
mic_audio_file = "temp_audio.wav"

# ============================
# Ask for webcam and mic usage
# ============================
def prompt_user_options():
    global use_webcam, use_microphone

    cam_input = input("Do you want to enable webcam? (y/n): ").lower()
    mic_input = input("Do you want to enable microphone? (y/n): ").lower()
    valid = ['y', 'n']

    if cam_input not in valid or mic_input not in valid:
        print("❌ Please enter valid input (y/n)")
        sys.exit(1)

    use_webcam = cam_input == 'y'
    use_microphone = mic_input == 'y'

# ============================
# Webcam Thread
# ============================
def webcam_thread():
    global webcam_frame , webcam_running
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Webcam not found.")
        return

    webcam_running = True
    while webcam_running:
        ret, frame = cam.read()
        if ret:
            webcam_frame = cv2.resize(frame, (160, 120))
    cam.release()

# ============================
# Start microphone recording with good quality (hidden output)
# ============================
def start_mic_recording():
    global mic_process
    if os.name == "nt":
        audio_input = "audio=" + get_windows_default_mic()
        mic_command = [
            "ffmpeg", "-y",
            "-f", "dshow",
            "-i", audio_input,
            "-ac", "2",
            "-ar", "44100",
            mic_audio_file
        ]
    else:
        mic_command = [
            "ffmpeg", "-y",
            "-f", "pulse",
            "-i", "default",
            "-ac", "2",
            "-ar", "44100",
            mic_audio_file
        ]

    mic_process = subprocess.Popen(mic_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ============================
# Stop microphone recording and merge with video
# ============================
def stop_mic_recording():
    global mic_process, output_path
    final_output = output_path.replace(".mp4", "_with_audio.mp4")

    if mic_process:
        mic_process.terminate()
        mic_process.wait()

    if os.path.exists(mic_audio_file):
        print("🔄 Merging audio with video...")
        merge_cmd = [
            "ffmpeg", "-y",
            "-i", output_path,
            "-i", mic_audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            final_output
        ]
        subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(mic_audio_file)
        os.remove(output_path)
        os.rename(final_output, output_path)
        print("✅ Merged audio into video.")

# ============================
# Get default microphone name on Windows
# ============================
def get_windows_default_mic():
    try:
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True
        )
        for line in result.stderr.splitlines():
            if "Microphone" in line or "Audio" in line:
                return line.split('"')[1]
    except:
        return "default"
    return "default"

# ============================
# Overlay webcam on frame if enabled
# ============================
def overlay_webcam(frame):
    global webcam_frame
    if use_webcam and webcam_frame is not None:
        h, w, _ = frame.shape
        resized = cv2.resize(webcam_frame, (160, 120))
        frame[10:130, w - 170:w - 10] = resized
    return frame

# ============================
# Record a selected monitor
# ============================
def record_selected_monitor():
    global width, height, out, output_path, paused
    prompt_user_options()

    if use_webcam:
        threading.Thread(target=webcam_thread, daemon=True).start()

    if use_microphone:
        start_mic_recording()

    with mss.mss() as sct:
        monitors = sct.monitors
        for i, monitor in enumerate(monitors):
            print(f"[{i}] - {monitor}")

        try:
            index = int(input("Enter monitor number to record: "))
            monitor = monitors[index]
        except (ValueError, IndexError):
            print("❌ Invalid monitor selection.")
            return

        width = monitor["width"]
        height = monitor["height"]
        prepare_output_file(width, height)

        print("Recording monitor... Press P to pause/resume, Q to quit.")
        try:
            while True:
                img = sct.grab(monitor)
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
                if not paused:
                    frame = overlay_webcam(frame)
                    out.write(frame)
                else:
                    cv2.putText(frame, "Paused", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
                cv2.imshow("Recording Monitor", frame)

                key = cv2.waitKey(1)
                if key == ord("q"):
                    break
                elif key == ord("p"):
                    paused = not paused
                    print("⏸️ Paused" if paused else "▶️ Resumed")

        except KeyboardInterrupt:
            print("🛑 Recording interrupted.")

        out.release()
        cv2.destroyAllWindows()

        if use_microphone:
            stop_mic_recording()

        print(f"✅ Recording saved to: {output_path}")

# ============================
# Create filename and writer
# ============================
def prepare_output_file(w, h):
    global out, output_path
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"record_{timestamp}.mp4"
    output_dir = os.path.join(input("Enter Your Path : "))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (w, h))

    if not out.isOpened():
        print("❌ Failed to open video writer.")
        exit()

# ================
# Main App Window
# ================
def Main():
    print("================================")
    print("Welcome to SRecorder By SayyadN")
    print("================================")
    print("1. Record Monitor")
    user_num = int(input("Enter Your Number of Operation: "))
    if user_num == 1:
        record_selected_monitor()
    else:
        print("Invalid Input")

Main()
