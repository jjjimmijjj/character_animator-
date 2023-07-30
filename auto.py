import time
import pyautogui
import simpleaudio as sa
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import wave

# Global variables
watched_directory = r'F:\oogabooga\oobabooga_windows\text-generation-webui\extensions\silero_tts\outputs'
current_file_length = 0
audio_playing = False

def play_sound(sound_file):
    wave_obj = sa.WaveObject.from_wave_file(sound_file)
    play_obj = wave_obj.play()
    play_obj.wait_done()

def move_mouse_and_click(x, y):
    pyautogui.moveTo(x, y)
    pyautogui.click()

def analyze_file_length(file_path):
    try:
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            duration = frames / frame_rate
            return duration
    except Exception as e:
        print(f"An error occurred while analyzing file length: {e}")
        return 0

def is_audio_playing():
    return audio_playing

def handle_new_file(event):
    global current_file_length
    if not event.is_directory and event.event_type == 'created' and event.src_path.endswith('.wav'):
        file_path = event.src_path
        length = analyze_file_length(file_path)
        current_file_length = length
        print(f"New file detected: {file_path}, length: {current_file_length} seconds")

def main():
    base_sleep_time = 1  # Base sleep time before repeating the cycle
    
    event_handler = FileSystemEventHandler()
    event_handler.on_created = handle_new_file
    
    observer = Observer()
    observer.schedule(event_handler, path=watched_directory, recursive=False)
    observer.start()
    
    while True:
        try:
            # Move mouse and click at specified location
            move_mouse_and_click(3960, 941)
            
            # Play "ale.wav" sound indicating mouse button press
            sound_file = r'C:\Users\Jim\Documents\GitHub\auto\ale.wav'
            play_sound(sound_file)
            
            # Wait for 10 seconds
            time.sleep(9)
            
            # Move mouse and click again
            move_mouse_and_click(3960, 941)
            
            # Play "ting.wav" sound indicating mouse button press
            sound_file = r'C:\Users\Jim\Documents\GitHub\auto\ting.wav'
            play_sound(sound_file)
            
            # Wait for 13 seconds for the ai to think
            time.sleep(12)
            
            # Wait for the current file's length
            time.sleep(current_file_length)
            
            # Adjust sleep time based on file length
            if current_file_length < 5:
                sleep_time = base_sleep_time / 2
            else:
                sleep_time = base_sleep_time
            
            # Wait for the audio to finish playing
            while is_audio_playing():
                time.sleep(1)
            
            # Sleep time before repeating the cycle
            time.sleep(sleep_time)
            
        except KeyboardInterrupt:
            print("Script stopped by user.")
            break
    
    observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
