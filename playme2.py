import os
import random
import subprocess
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import wave
from functools import partial




# Define the paths and constants
base_video_directory = "F:/oogabooga/wav2lip/Wav2Lip/basevideos"
audio_directory = "F:/oogabooga/oobabooga_windows/text-generation-webui/text-generation-webui\extensions/silero_tts/outputs"
checkpoint_path = "F:/oogabooga/wav2lip/Wav2Lip/checkpoints/wav2lip_gan.pth"
destination_folder = r"F:\oogabooga\wav2lip\Wav2Lip\results\played"

 
def generate_command_line(video_path, audio_path):
    # Get a random video file from the base video directory
    video_files = os.listdir(video_path) # Use video_path as a directory
    random_video_file = random.choice(video_files)
    video_file = os.path.join(video_path, random_video_file) # Use video_file as a file

    # Get a random audio file from the audio directory
    audio_files = os.listdir(audio_path)
    while not audio_files:  # Wait for audio files to be available
        print("No audio files found. Waiting for 10 seconds...")
        time.sleep(10)
        audio_files = os.listdir(audio_path)

    random_audio_file = random.choice(audio_files)
    audio_file = os.path.join(audio_path, random_audio_file)

    # Build the command line as a list of strings
    command_parts = ["python", "inference.py", "--checkpoint_path", checkpoint_path, "--face", video_file.replace("\\", "/"), "--audio", audio_file.replace("\\", "/")]
    return command_parts
def start_inference(command_line):
    global inference_process
    inference_process = subprocess.Popen(command_line, shell=True)
    inference_process.communicate()
def stop_inference():
    global inference_process
    if inference_process is not None and inference_process.poll() is None:
        inference_process.terminate()
        inference_process.wait()
        inference_process = None
class FileEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            if filename.lower().endswith('.mp4'):
                print(f"New .mp4 file detected: {filename}")
                stop_inference()
                main()  # Restart the inference process
                
                
def process_wav_file(wav_file, video_path, audio_path):
    # Generate the command line (you can keep this as it is)
    command_line = generate_command_line(base_video_directory, audio_directory)

    # Start the inference process with the command line
    subprocess.run(command_line)

   
def main():
    # Your existing code to generate the command line
    command_line = generate_command_line(base_video_directory, audio_directory)
    
    # Print the generated command line
    print("Generated command line:", command_line)

    # Your existing code to start the inference
    start_inference(command_line)

if __name__ == "__main__":
    # Initialize the file system event handler
    event_handler = FileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=destination_folder, recursive=False)
    observer.start()

    try:
        main()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()






    