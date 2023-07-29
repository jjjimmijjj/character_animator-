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
audio_directory = "F:/oogabooga/oobabooga_windows/text-generation-webui/text-generation-webui/extensions/silero_tts/outputs"
checkpoint_path = "F:/oogabooga/wav2lip/Wav2Lip/checkpoints/wav2lip_gan.pth"
destination_folder = r"F:\oogabooga\wav2lip\Wav2Lip\results\played"
base_video_directory2 = "F:/oogabooga/wav2lip/Wav2Lip/basevideos2"

def generate_command_line(audio_path):
    # Initialize command_parts to an empty list
    command_parts = []

    # Get a random audio file from the audio directory
    audio_files = os.listdir(audio_path)
    while not audio_files:  # Wait for audio files to be available
        print("No audio files found. Waiting for 10 seconds...")
        time.sleep(10)
        audio_files = os.listdir(audio_path)

    random_audio_file = random.choice(audio_files)
    audio_file = os.path.join(audio_path, random_audio_file)

    # Get a random video file from the base video directory based on audio file name
    if "wirginia" in random_audio_file:
        video_files = os.listdir(base_video_directory)
        base_video_path = base_video_directory
        print("Selected base_video_directory:", base_video_directory)
    elif "cupie" in random_audio_file:
        video_files = os.listdir(base_video_directory2)
        base_video_path = base_video_directory2
        print("Selected base_video_directory2:", base_video_directory2)
    else:
        # If neither "wirginia" nor "cupie" is in the audio file name, use the default base_video_directory
        video_files = os.listdir(base_video_directory)
        base_video_path = base_video_directory
        print("Selected default base_video_directory:", base_video_directory)

    random_video_file = random.choice(video_files)
    video_file = os.path.join(base_video_path, random_video_file)

    # Replace backslashes with forward slashes only if video_file is assigned
    command_parts.extend([
        "python", "inference.py",
        "--checkpoint_path", checkpoint_path,
        "--face", video_file.replace("\\", "/"),
        "--audio", audio_file.replace("\\", "/")
    ])

    # Return the generated command line as a list of arguments
    return command_parts, video_file


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
    command_line, video_file = generate_command_line(base_video_directory, audio_directory)

    # Start the inference process with the command line
    subprocess.run(command_line)

   
def main():
    # Get a random video file from the base_video_directory
    video_files = os.listdir(base_video_directory)
    random_video_file = random.choice(video_files)
    video_file = os.path.join(base_video_directory, random_video_file)

    # Get a random audio file from the audio_directory
    audio_files = os.listdir(audio_directory)
    while not audio_files:  # Wait for audio files to be available
        print("No audio files found. Waiting for 10 seconds...")
        time.sleep(10)
        audio_files = os.listdir(audio_directory)

    random_audio_file = random.choice(audio_files)
    audio_file = os.path.join(audio_directory, random_audio_file)

    # Generate the command line using the paths and variables
    command_line, video_file = generate_command_line(audio_directory)  # Pass audio_directory instead of base_video_directory

    # Print the values used in the command line (optional)
    print("checkpoint_path:", checkpoint_path)
    print("video_file:", video_file)
    print("audio_file:", audio_file)

    # Print the generated command line (optional)
    print("Generated command line:", command_line)

    # Start the inference process
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






    