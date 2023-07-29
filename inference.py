from os import listdir, path
import numpy as np
import scipy, cv2, os, sys, argparse, audio
import json, subprocess, random, string
from tqdm import tqdm
from glob import glob
import torch, face_detection
from models import Wav2Lip
import platform
import time 
import shutil
import audio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import datetime
import moviepy
from moviepy.editor import VideoFileClip
from torch.cuda.amp import autocast

parser = argparse.ArgumentParser(description='Inference code to lip-sync videos in the wild using Wav2Lip models')

parser.add_argument('--checkpoint_path', type=str, 
					help='Name of saved checkpoint to load weights from', required=True)

parser.add_argument('--face', type=str, 
					help='Filepath of video/image that contains faces to use', required=True)
parser.add_argument('--audio', type=str, 
					help='Filepath of video/audio file to use as raw audio source', required=True)
parser.add_argument('--outfile', type=str, help='Video path to save result. See default for an e.g.', 
								default='results/result_voice.mp4')
parser.add_argument('--img_size', type=int, default=96, help="Size of the input image to the model.")

parser.add_argument('--static', type=bool, 
					help='If True, then use only first video frame for inference', default=False)
parser.add_argument('--fps', type=float, help='Can be specified only if input is a static image (default: 25)', 
					default=25., required=False)

parser.add_argument('--pads', nargs='+', type=int, default=[0, 10, 0, 0], 
					help='Padding (top, bottom, left, right). Please adjust to include chin at least')

parser.add_argument('--face_det_batch_size', type=int, 
					help='Batch size for face detection', default=16)
parser.add_argument('--wav2lip_batch_size', type=int, help='Batch size for Wav2Lip model(s)', default=128)

parser.add_argument('--resize_factor', default=1, type=int, 
			help='Reduce the resolution by this factor. Sometimes, best results are obtained at 480p or 720p')

parser.add_argument('--crop', nargs='+', type=int, default=[0, -1, 0, -1], 
					help='Crop video to a smaller region (top, bottom, left, right). Applied after resize_factor and rotate arg. ' 
					'Useful if multiple face present. -1 implies the value will be auto-inferred based on height, width')

parser.add_argument('--box', nargs='+', type=int, default=[-1, -1, -1, -1], 
					help='Specify a constant bounding box for the face. Use only as a last resort if the face is not detected.'
					'Also, might work only if the face is not moving around much. Syntax: (top, bottom, left, right).')

parser.add_argument('--rotate', default=False, action='store_true',
					help='Sometimes videos taken from a phone can be flipped 90deg. If true, will flip video right by 90deg.'
					'Use if you get a flipped result, despite feeding a normal looking video')

parser.add_argument('--nosmooth', default=False, action='store_true',
					help='Prevent smoothing face detections over a short temporal window')

args = parser.parse_args()

if os.path.isfile(args.face) and args.face.split('.')[1] in ['jpg', 'png', 'jpeg']:
	args.static = True

def get_smoothened_boxes(boxes, T):
	for i in range(len(boxes)):
		if i + T > len(boxes):
			window = boxes[len(boxes) - T:]
		else:
			window = boxes[i : i + T]
		boxes[i] = np.mean(window, axis=0)
	return boxes

def face_detect(images):
	detector = face_detection.FaceAlignment(face_detection.LandmarksType._2D, 
											flip_input=False, device=device)

	batch_size = args.face_det_batch_size
	
	while 1:
		predictions = []
		try:
			for i in tqdm(range(0, len(images), batch_size)):
				predictions.extend(detector.get_detections_for_batch(np.array(images[i:i + batch_size])))
		except RuntimeError:
			if batch_size == 1: 
				raise RuntimeError('Image too big to run face detection on GPU. Please use the --resize_factor argument')
			batch_size //= 2
			print('Recovering from OOM error; New batch size: {}'.format(batch_size))
			continue
		break

	results = []
	pady1, pady2, padx1, padx2 = args.pads
	for rect, image in zip(predictions, images):
		if rect is None:
			cv2.imwrite('temp/faulty_frame.jpg', image) # check this frame where the face was not detected.
			raise ValueError('Face not detected! Ensure the video contains a face in all the frames.')

		y1 = max(0, rect[1] - pady1)
		y2 = min(image.shape[0], rect[3] + pady2)
		x1 = max(0, rect[0] - padx1)
		x2 = min(image.shape[1], rect[2] + padx2)
		
		results.append([x1, y1, x2, y2])

	boxes = np.array(results)
	if not args.nosmooth: boxes = get_smoothened_boxes(boxes, T=5)
	results = [[image[y1: y2, x1:x2], (y1, y2, x1, x2)] for image, (x1, y1, x2, y2) in zip(images, boxes)]

	del detector
	return results 

def datagen(frames, mels):
	img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

	if args.box[0] == -1:
		if not args.static:
			face_det_results = face_detect(frames) # BGR2RGB for CNN face detection
		else:
			face_det_results = face_detect([frames[0]])
	else:
		print('Using the specified bounding box instead of face detection...')
		y1, y2, x1, x2 = args.box
		face_det_results = [[f[y1: y2, x1:x2], (y1, y2, x1, x2)] for f in frames]

	for i, m in enumerate(mels):
		idx = 0 if args.static else i%len(frames)
		frame_to_save = frames[idx].copy()
		face, coords = face_det_results[idx].copy()

		face = cv2.resize(face, (args.img_size, args.img_size))
			
		img_batch.append(face)
		mel_batch.append(m)
		frame_batch.append(frame_to_save)
		coords_batch.append(coords)

		if len(img_batch) >= args.wav2lip_batch_size:
			img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

			img_masked = img_batch.copy()
			img_masked[:, args.img_size//2:] = 0

			img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
			mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

			yield img_batch, mel_batch, frame_batch, coords_batch
			img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

	if len(img_batch) > 0:
		img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

		img_masked = img_batch.copy()
		img_masked[:, args.img_size//2:] = 0

		img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
		mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

		yield img_batch, mel_batch, frame_batch, coords_batch

mel_step_size = 16
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print('Using {} for inference.'.format(device))

def _load(checkpoint_path):
	if device == 'cuda':
		checkpoint = torch.load(checkpoint_path)
	else:
		checkpoint = torch.load(checkpoint_path,
								map_location=lambda storage, loc: storage)
	return checkpoint

def load_model(path):
	model = Wav2Lip()
	print("Load checkpoint from: {}".format(path))
	checkpoint = _load(path)
	s = checkpoint["state_dict"]
	new_s = {}
	for k, v in s.items():
		new_s[k.replace('module.', '')] = v
	model.load_state_dict(new_s)

	model = model.to(device)
	return model.eval()


# Source and destination folders for video files
source_folder = r"F:\oogabooga\wav2lip\Wav2Lip\results"
destination_folder = r"F:\oogabooga\wav2lip\Wav2Lip\results\played"

# List of video file extensions to handle
media_extension = [".mp4"]

# Media player path
media_player = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
output_path = "F:/oogabooga/REPOSITORY/completedaudio"
audio_path = args.audio
completed_directory = "F:/oogabooga/REPOSITORY/completedaudio"
audio_file = os.path.basename(args.audio)
result_directory = "F:/oogabooga/wav2lip/Wav2Lip/results"

output_folder = r"F:\oogabooga\wav2lip\Wav2Lip\results"

#class FileEventHandler(FileSystemEventHandler):
  #  def on_created(self, event):
   #     if not event.is_directory:
    #        filename = os.path.basename(event.src_path)
     #       if filename.lower().endswith(tuple(media_extension)):
      #          play_and_move(filename)

def duration():
    # Play the output video using the media player
   # command = [media_player, "-f", "--no-video-title", args.outfile]
   # subprocess.Popen(command, shell=False)

    #Get the video's duration using moviepy
    video_clip = VideoFileClip(args.outfile)
    duration = video_clip.duration
    video_clip.close()

    return duration

def terminate_player_process(player_name):
    # Terminate the player process with the given name
    try:
        subprocess.call(['taskkill', '/F', '/IM', player_name])
        print(f"Successfully terminated {player_name} process")
    except Exception as e:
        print(f"Error occurred while terminating {player_name} process: {e}")
    
def play_and_move(file):
    file_path = os.path.join(source_folder, file)
    new_file_path = os.path.join(destination_folder, file)

    # Open the file with VLC in full-screen mode and enable play-and-exit
    command = [media_player, "-f", "--no-video-title", "--play-and-exit", file_path]
    player_process = subprocess.Popen(command, shell=False)

    # Wait until the player process terminates
    player_process.wait()

    # Move the file to the destination folder
    for i in range(10):
        try:
            shutil.move(file_path, new_file_path)
            break  # Exit the loop if move is successful
        except Exception as e:
            print(f"Error occurred while moving the file: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    face_name = os.path.basename(args.face).split('.')[0]
    audio_name = os.path.basename(args.audio).split('.')[0]
    output_filename = f"x_{face_name}_{audio_name}_{timestamp}.mp4"
    args.outfile = os.path.join(result_directory, output_filename)
    
    time.sleep(1)

    if not os.path.isfile(args.face):
        raise ValueError('--face argument must be a valid path to video/image file')

    elif args.face.split('.')[1] in ['jpg', 'png', 'jpeg']:
        full_frames = [cv2.imread(args.face)]
        fps = args.fps

    else:
        video_stream = cv2.VideoCapture(args.face)
        fps = video_stream.get(cv2.CAP_PROP_FPS)

        print('Reading video frames...')

        full_frames = []
        while 1:
            still_reading, frame = video_stream.read()
            if not still_reading:
                video_stream.release()
                break
            if args.resize_factor > 1:
                frame = cv2.resize(frame, (frame.shape[1] // args.resize_factor, frame.shape[0] // args.resize_factor))

            if args.rotate:
                frame = cv2.rotate(frame, cv2.cv2.ROTATE_90_CLOCKWISE)

            y1, y2, x1, x2 = args.crop
            if x2 == -1:
                x2 = frame.shape[1]
            if y2 == -1:
                y2 = frame.shape[0]

            frame = frame[y1:y2, x1:x2]

            full_frames.append(frame)

    print("Number of frames available for inference: " + str(len(full_frames)))
    
    
    



    if not args.audio.endswith('.wav'):
      print('Extracting raw audio...')
      command = 'ffmpeg -y -i {} -strict -2 {}'.format(args.audio, 'temp/temp.wav')

      subprocess.call(command, shell=True)
      args.audio = 'temp/temp.wav'

    wav = audio.load_wav(args.audio, 16000)
    mel = audio.melspectrogram(wav)
    print(mel.shape)

    if np.isnan(mel.reshape(-1)).sum() > 0:
      raise ValueError('Mel contains nan! Using a TTS voice? Add a small epsilon noise to the wav file and try again')

    mel_chunks = []
    mel_idx_multiplier = 80./fps 
    i = 0
    while 1:
      start_idx = int(i * mel_idx_multiplier)
      if start_idx + mel_step_size > len(mel[0]):
        mel_chunks.append(mel[:, len(mel[0]) - mel_step_size:])
        break
      mel_chunks.append(mel[:, start_idx : start_idx + mel_step_size])
      i += 1

    print("Length of mel chunks: {}".format(len(mel_chunks)))

    full_frames = full_frames[:len(mel_chunks)]

    batch_size = args.wav2lip_batch_size
    gen = datagen(full_frames.copy(), mel_chunks)

    for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(gen, total=int(np.ceil(float(len(mel_chunks))/batch_size)))):
        if i == 0:
            model = load_model(args.checkpoint_path)
            print("Model loaded")

            frame_h, frame_w = full_frames[0].shape[:-1]
            out = cv2.VideoWriter('temp/result.avi', cv2.VideoWriter_fourcc(*'DIVX'), fps, (frame_w, frame_h))

        img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(device)
        mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(device)

        with torch.no_grad():
            pred = model(mel_batch, img_batch)

        pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.

        for p, f, c in zip(pred, frames, coords):
            y1, y2, x1, x2 = c
            p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))

            f[y1:y2, x1:x2] = p
            out.write(f)

    out.release()

    command = 'ffmpeg -y -i {} -i {} -strict -2 -q:v 1 {}'.format(args.audio, 'temp/result.avi', args.outfile)
    subprocess.call(command, shell=platform.system() != 'Windows')

    # Play the output video
   # play_output_video()
   
    # Move the result file to this folder
    #result_path = os.path.join("F:/oogabooga/wav2lip/Wav2Lip", args.outfile)
   # if result_path != output_path:
   #     shutil.move(result_path, result_directory)
   # else:
    #    print("Source and destination paths are the same. Skipping move operation.")
    shutil.move(audio_path, os.path.join(completed_directory, audio_file)) 
    #shutil.move(result_path, destination_folder)
    #terminate_player_process(media_player)
    # Terminate the VLC process after video playback
    


    # Move and play existing videos in the source folder
    for file in os.listdir(source_folder):
        if file.lower().endswith(tuple(media_extension)):
            play_and_move(file)
    # Add a delay before calling the termination function
    time.sleep(5)

    # Call the termination function after the video playback is finished
    terminate_player_process("vlc.exe")      
         
    # Inside the loop of the main() function
    torch.cuda.empty_cache()
# Define other variables here (source_folder, destination_folder, media_extension, media_player)

if __name__ == '__main__':
    
 #   args = parser.parse_args()
   
    main()       

    # Add a delay before playing the video
   # time.sleep(2)

    ## Play the output video and get its duration
   # video_duration = play_output_video()

   # # Wait for the video to finish playing (use its duration)
   # time.sleep(video_duration)

    

    # Move and play existing videos in the source folder
   # for file in os.listdir(source_folder):
     #   if file.lower().endswith(tuple(media_extension)):
      #      play_and_move(file)
            
    # Move the result file to the destination folder
   # result_path = os.path.join("F:/oogabooga/wav2lip/Wav2Lip", args.outfile)
    #if result_path != output_path:
    #    shutil.move(result_path, result_directory)
    #else:
   #     print("Source and destination paths are the same. Skipping move operation.")
    #shutil.move(audio_path, os.path.join(completed_directory, audio_file)) 
    #terminate_player_process(media_player)        