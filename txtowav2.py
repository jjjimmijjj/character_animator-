import os
import torch
import shutil

device = torch.device('cpu')
torch.set_num_threads(4)
local_file = 'model.pt'

if not os.path.isfile(local_file):
    torch.hub.download_url_to_file('https://models.silero.ai/models/tts/en/v3_en.pt', local_file)

model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
model.to(device)

# Function to extract the first word or first two words combined without spaces from a line
def get_filename_from_line(line):
    words = line.strip().split()
    if len(words) >= 2:
        return 'cupie_' + ''.join(words[:2])
    elif len(words) == 1:
        return 'cupie_' + words[0]
    else:
        return None

# Function to generate speech for each line in the text file
def generate_speech_from_file(file_path, output_folder):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    used_filenames = set()

    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            # Generate the speech audio
            audio_path = model.save_wav(text=line, speaker='en_69', sample_rate=48000)

            # Get the filename based on the first word or first two words of the line
            filename = get_filename_from_line(line)

            if filename is None:
                # Skip lines with no words
                continue

            # Remove spaces from the filename
            filename = filename.replace(' ', '')

            # Handle duplicate filenames by appending a number to the filename
            count = 1
            original_filename = filename
            while filename in used_filenames:
                filename = f'{original_filename}_{count}'
                count += 1

            used_filenames.add(filename)

            # Save the WAV file to the specified folder
            output_file = os.path.join(output_folder, f'{filename}_output_{i}.wav')

            try:
                with open(output_file, 'wb') as f:
                    shutil.copy(audio_path, output_file)  # Copy the audio file from the generated path to the output path

                print(f"Generated speech for line {i+1}: {line}")
            except Exception as e:
                print(f"Error while writing WAV file {output_file}: {e}")

# Replace 'output_folder' with the desired folder path where you want to save the generated WAV files
output_folder = 'I:/cupie/output_audio'
file_path = 'I:/cupie/cupie.txt'
# Call the function to generate speech from the text file
generate_speech_from_file(file_path, output_folder)



