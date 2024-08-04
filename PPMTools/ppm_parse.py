import os
import glob
import subprocess # FFMPEG
import json
import wave
import audioop
import numpy as np

from . import ppm_helpers
from . import ppm_except

HAS_PIL = False
HAS_MOVIEPY = False
HAS_FFMPEG = False

# Import PIL if we have it
try:
	from PIL import Image
	HAS_PIL = True
except ImportError:
	print("Please install PIL to extract images (pip install pllow)")

# Import moviepy if we have it
try:
	from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip
	HAS_MOVIEPY = True
except ImportError:
	print("Please install moviepy in order to combine exported frames and audio into video or GIF formats (pip install moviepy)")

# Test for FFMPEG in the path
try:
	with open(os.devnull,"w") as null:
		subprocess.call(["ffmpeg","-h"], stdout=null, stderr=null)
		
	HAS_FFMPEG = True
except OSError:
	print("Please install FFMPEG and include its location in your PATH variable so you can export video (https://www.ffmpeg.org/download.html)")
	

# PPM Class
class PPM:

	# Initialize
	def __init__(self) -> None:
		"""
		PPM Parser Class
		----------------

		Parse PPM files!
		"""

		self.Loaded = {
			"Metadata": False,
			"Frames": False,
			"Sound": False,
		}
		self.Frames = None
		self.Thumbnail = None
		self.RawThumbnail = None
		self.SoundData = None
		self.InputFileName = None

	# Read flipnote PPM file
	def ReadFile(
			self,
			path: str | os.PathLike,
			DecodeThumbnail: bool = True,
			ReadFrames: bool = True,
			ReadSound: bool = True):
		"""
		Read Flipnote from PPM file

		The PPM file will be read as bytes and sent to `PPM.ReadBytes()`.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		data : str | os.PathLike
			Path to Flipnote PPM file
		DecodeThumbnail : bool (defualt = `True`)
			If true, decode the Flipnote's thumbnail
		ReadFrames : bool (defualt = `True`)
			If true, decode the Flipnote's frames
		ReadSound : bool (defualt = `True`)
			If true, decode the Flipnote's sound data
		
		Returns
		-------
		out : ppm_parser.PPM
			PPM Instance
		"""

		self.InputFileName = os.path.basename(path)

		with open(path, "rb") as f:
			return self.ReadBytes(f.read(), DecodeThumbnail, ReadFrames, ReadSound)
	
	# Read flipnote bytes
	def ReadBytes(
			self,
			data: bytes,
			DecodeThumbnail: bool = True,
			ReadFrames: bool = True,
			ReadSound: bool = True):
		"""
		Read Flipnote from bytes.

		If you want to read a PPM file, use `PPM.ReadFile()` instead.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		data : bytes
			Bytes of Flipnote
		DecodeThumbnail : bool (defualt = `True`)
			If true, decode the Flipnote's thumbnail
		ReadFrames : bool (defualt = `True`)
			If true, decode the Flipnote's frames
		ReadSound : bool (defualt = `True`)
			If true, decode the Flipnote's sound data
		
		Returns
		-------
		out : ppm_parser.PPM
			PPM Instance
		"""

		# Ensure data is PPM
		if data[:4] != b"PARA": # Check header magic
			raise ppm_except.PPMBinaryNotValid(message=f"Header magic is \"{data[:4]}\" instead of \"PARA\".")
		if len(data) <= 0x6a0: # Check PPM data length
			raise ppm_except.PPMBinaryNotValid(message=f"Data is {len(data)} bytes long, it should be {str(int(0x6a0))} or longer.")
		
		# Read audio data
		Audio_Offset = ppm_helpers.AscDec(data[4:8], True) + 0x6a0
		Audio_Length = ppm_helpers.AscDec(data[8:12], True)

		# Get frame count
		self.FrameCount = ppm_helpers.AscDec(data[12:14], True) + 1

		# Set to true if locked, false otherwise
		self.Locked = data[0x10] & 0x01 == 1

		# The frame index of the thumbnail
		self.ThumbnailFrameIndex = ppm_helpers.AscDec(data[0x12:0x14], True)
		
		# Contributor names
		self.OriginalAuthorName = str(ppm_helpers.DecodeString(data[0x14:0x2A]))
		self.EditorAuthorName = str(ppm_helpers.DecodeString(data[0x2A:0x40]))
		self.Username = str(ppm_helpers.DecodeString(data[0x40:0x56]))

		# Contributor ID's
		self.OriginalAuthorID = str(ppm_helpers.ToHex(data[0x56:0x5e][::-1]))[2:-1]
		self.EditorAuthorID = str(ppm_helpers.ToHex(data[0x5E:0x66][::-1]))[2:-1]

		# ID of the previous editor(?)
		self.PreviousEditAuthorID = str(ppm_helpers.ToHex(data[0x8a:0x92][::-1]))[2:-1]

		# Filenames (compressed)
		self.OriginalFilenameC = data[0x66:0x78]
		self.CurrentFilenameC = data[0x78:0x8a]

		# Get Filenames from compressed names
		self.OriginalFilename = ppm_helpers.FilenameToString(ppm_helpers.DecompressFilename(self.OriginalFilenameC))
		self.CurrentFilename = ppm_helpers.FilenameToString(ppm_helpers.DecompressFilename(self.CurrentFilenameC))

		# Get embedded date
		self.Date = ppm_helpers.FormattedDateFromEpoch(data[0x9a:0x9e])

		# Get raw thumbnail data, and decode it if the user asked to
		self.RawThumbnail = data[0xa0:0x6a0]
		if DecodeThumbnail:
			self.GetThumbnail()

		# Mark metadata as loaded
		self.Loaded["Metadata"] = True

		# True if the flipnote loops, false otherwise
		self.Looped = data[0x06A6] >> 1 & 0x01 == 1

		# Read animation sequence header
		Animation_Offset = 0x6a8 + ppm_helpers.AscDec(data[0x6a0:0x6a4], True)
		Frame_Offsets = [Animation_Offset + ppm_helpers.AscDec(data[0x06a8+i*4:0x06a8+i*4+4], True) for i in range(self.FrameCount)]

		# Read what frames have SFX
		self.SFXUsage = [(i&0x1!=0, i&0x2!=0, i&0x4!=0) for i in data[Audio_Offset:Audio_Offset+self.FrameCount]]

		ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 0)

		Sound_Size = (
			ppm_helpers.AscDec(data[
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 0):
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 0, True)], True), # BGM
			ppm_helpers.AscDec(data[
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 4):
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 4, True)], True), # SFX1
			ppm_helpers.AscDec(data[
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 8):
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 8, True)], True), # SFX2
			ppm_helpers.AscDec(data[
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 12):
				ppm_helpers.GetSoundSize(Audio_Offset, self.FrameCount, 12, True)], True) # SFX3
		)

		# Get framespeed
		self.Framespeed = 8 - data[ppm_helpers.AddPadding(Audio_Offset+self.FrameCount, 4) + 16]
		self.BGMFramespeed = 8 - data[ppm_helpers.AddPadding(Audio_Offset+self.FrameCount, 4) + 17]

		# Decode frames if the user asked to
		if ReadFrames:
			self.Frames = []
			for i, offset in enumerate(Frame_Offsets):
				#Read frame header
				Inverted = data[offset] & 0x01 == 0
				
				#Reads which color that will be used
				Colors = (
					data[offset] >> 1 & 0x03,
					data[offset] >> 3 & 0x03
				)
				
				Frame = self.ExtractFrame(data, offset, self.Frames[i-1][2] if i else None)
				
				self.Frames.append([Inverted, Colors, Frame])
			
			# Mark frames as loaded
			self.Loaded["Frames"] = True

		#Read the Audio:
		if ReadSound:
			self.SoundData = []
			pos = ppm_helpers.AddPadding(Audio_Offset+self.FrameCount+32, 4)
			for i in range(4):
				self.SoundData.append(data[pos:pos+Sound_Size[i]])
				pos += Sound_Size[i]
			
			# Mark sounds as loaded
			self.Loaded["Sound"] = True

		return self
	
	# Get a single frame
	def GetFrame(self, frame_index: int) -> np.ndarray[bytes]:
		"""
		Get a single frame from the loaded Flipnote data.

		This will only work if `self.ReadFrames = True` when using `PPM.ReadFile()` or `PPM.ReadBytes()`

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		frame_index : int
			Index of the desired frame
		
		Returns
		-------
		out : ndarray[bytes]
			Single frame
		"""

		# Check that frames were loaded
		if not self.Loaded["Frames"]:
			raise ppm_except.PPMDataNotLoaded("Frames")
		
		inverted, colors, frame = self.Frames[frame_index]
		
		# Defines the palette:
		palette = ppm_helpers.FRAME_PALETTE[:]
		if inverted:
			palette[0], palette[1] = palette[1], palette[0]

		color_primary = palette[colors[0]]
		color_secondary = palette[colors[1]]
		
		out = np.zeros((256, 192), dtype=">u4")
		out[:] = palette[0]
		out[frame[1]] = color_secondary
		out[frame[0]] = color_primary
		
		return out
	
	# Get the thumbnail
	def GetThumbnail(self) -> np.ndarray[bytes]:
		"""
		Get the thumbnail of the loaded Flipnote data.

		This will only work if `self.DecodeThumbnail = True` when using `PPM.ReadFile()` or `PPM.ReadBytes()`

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		
		Returns
		-------
		out : ndarray[bytes]
			Single frame
		"""

		if not self.RawThumbnail:
			ppm_except.PPMDataNotLoaded("Thumbnail")
		
		out = np.zeros((64, 48), dtype=">u4")
		
		#speedup:
		palette = ppm_helpers.THUMB_PALETTE
		
		#8x8 tiling:
		for ty in range(6):
			for tx in range(8):
				for y in range(8):
					for x in range(0,8,2):
						#two colors stored in each byte:
						byte = self.RawThumbnail[int((ty*512+tx*64+y*8+x)/2)]
						out[x+tx*8  , y+ty*8] = palette[byte & 0xF]
						out[x+tx*8+1, y+ty*8] = palette[byte >> 4]
		
		self.Thumbnail = out
		return self.Thumbnail
	
	def GetSound(self, sound_index: int, output_path: str | os.PathLike | None = None):
		"""
		Get a sound from the specified index in the Flipnote data.

		This will only work if `self.ReadSound = True` when using `PPM.ReadFile()` or `PPM.ReadBytes()`

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		sound_index : int
			Index of the desired sound.
			- 0 = BGM
			- 1 = SFX1
			- 2 = SFX2
			- 3 = SFX3
		output_path : str | os.PathLike | None
			Path to output the desired audio.
			If None, then it will be returned as bytes
		
		Returns
		-------
		out : bytes | None
			Sound data is returned as bytes if output_path = None
		"""

		if not self.Loaded["Sound"]:
			ppm_except.PPMDataNotLoaded("Sound")

		if self.SoundData[sound_index]:
			# Reverse nibbles:
			data = []
			for i in self.SoundData[sound_index]:
				data.append((i&0xF)<< 4 | (i>>4))
			
			data = bytes(data)
			
			# 4bit ADPCM decode
			decoded = audioop.adpcm2lin(data, 2, None)[0]
			
			# Output bytes if there is no output path
			if not output_path:
				return decoded

			# Name out file and concatenate it with output path
			out_file = os.path.join(output_path, f"{ppm_helpers.SOUND_NAMES[sound_index]}.wav")

			# Write wav file
			with wave.open(out_file, "wb") as f:
				f.setnchannels(1)
				f.setsampwidth(2)
				f.setframerate(8192)
				f.writeframes(decoded)

			return out_file
		
	# Extract frame
	def ExtractFrame(self, data: bytes, offset: int, prev_frame = None) -> np.ndarray:
		"""
		Extract a frame from the Flipnote data via its offset

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		data : bytes
			The PPM byte stream
		offset : int
			The head offset to used to seek through the data
		
		Returns
		-------
		out : ndarray
			Frame of flipnote
		"""
		
		Encoding = [[], []]
		Frame = np.zeros((2, 256, 192), dtype=np.bool_)
		
		# Read tags:
		New_Frame = data[offset] & 0x80 != 0
		Unknown = data[offset] >> 5 & 0x03
		
		offset += 1
		
		Frame_Move = [0,0]
		if Unknown & 0x2: # Doesn't work 100%...
			print("Frame_Move at offset ", offset-1)
			
			move_x = ppm_helpers.AscDec(data[offset+0:offset+1], True)
			move_y = ppm_helpers.AscDec(data[offset+1:offset+2], True)
			Frame_Move[0] = move_x if move_x <= 127 else move_x-256
			Frame_Move[1] = move_y if move_y <= 127 else move_y-256
			offset += 2
		elif Unknown:
			print("Unknown tags: ", Unknown, "at offset ", offset-1)
		
		# Read the line encoding of the layers:
		for layer in range(2):
			for byte in data[offset:offset+48]:
				Encoding[layer].append(byte      & 0x03)
				Encoding[layer].append(byte >> 2 & 0x03)
				Encoding[layer].append(byte >> 4 & 0x03)
				Encoding[layer].append(byte >> 6       )
			offset += 48
		
		# Read layers:
		for layer in range(2):
			for y in range(192):
				if Encoding[layer][y] == 0:#Nothing
					pass
				elif Encoding[layer][y] == 1:#Normal
					UseByte = ppm_helpers.AscDec(data[offset:offset+4])
					offset += 4
					x = 0
					while UseByte & 0xFFFFFFFF:
						if UseByte & 0x80000000:
							byte = data[offset]
							offset += 1
							for _ in range(8):
								if byte & 0x01:
									Frame[layer][x][y] = True
								x += 1
								byte >>= 1
						else:
							x += 8
						UseByte <<= 1
				elif Encoding[layer][y] == 2:#Inverted
					UseByte = ppm_helpers.AscDec(data[offset:offset+4])
					offset += 4
					x = 0
					while UseByte&0xFFFFFFFF:
						if UseByte & 0x80000000:
							byte = data[offset]
							offset += 1
							for _ in range(8):
								if not byte & 0x01:
									Frame[layer, x, y] = True
								x += 1
								byte >>= 1
						else:
							x += 8
						UseByte <<= 1
					for n in range(256):
						Frame[layer, n, y] = not Frame[layer, n, y]
				elif Encoding[layer][y] == 3:
					x = 0
					for _ in range(32):
						byte = data[offset]
						offset += 1
						for _ in range(8):
							if byte & 0x01:
								Frame[layer, x, y] = True
							x += 1
							byte >>= 1
		
		# Merges this frame with the previous frame if New_Frame isn't true:
		if not New_Frame and prev_frame.all() != None:# Maybe optimize this better for numpy...
			if Frame_Move[0] or Frame_Move[1]:# Moves the previous frame if specified:
				New_Prev_Frame = np.zeros((2, 256, 192), dtype=np.bool_)
				
				for y in range(192):# This still isn't perfected
					for x in range(256):
						Temp_X = x+Frame_Move[0]
						Temp_Y = y+Frame_Move[1]
						if 0 <= Temp_X < 256 and 0 <= Temp_Y < 192:
							New_Prev_Frame[0, Temp_X, Temp_Y] = prev_frame[0, x, y]
							New_Prev_Frame[1, Temp_X, Temp_Y] = prev_frame[1, x, y]
				
				prev_frame = New_Prev_Frame
			
			# Merge the frames:
			Frame = Frame != prev_frame
		
		return Frame
	
	def WriteImage(self, image: bytes, frame_index: int, output_path: str | os.PathLike) -> Image.Image:
		"""
		Write a PPM frame to a PNG image file using byte data and PIL

		Note: This function requires PIL to be installed. Install it via `pip install pillow`

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		image : bytes
			Image in bytes
		frame_index : int
			Index of the desired frame. Padded to 3 digits (e.g. `012` instead of `12`)
		output_path : str | os.PathLike
			Output path for the image
		
		Returns
		-------
		out : Image.Image
			PIL image of the desired frame
		"""

		global HAS_PIL

		if not HAS_PIL:
			raise ppm_except.PPMNoPIL()

		out = image.tostring("F")	
		out = Image.frombytes("RGBA", (len(image), len(image[0])), out)
		
		full_output_path = os.path.join(output_path, f"{str(frame_index).zfill(3)}.png")
		out.save(full_output_path, format="PNG")
		
		return out
	
	# Dump frames to PNG
	def DumpFrames(self, output_path: str | os.PathLike) -> None:
		"""
		Dump all frames in a PPM to PNG

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_path : str | os.PathLike
			Output path for the PNG images
		"""

		for i in range(self.FrameCount):
			print(f"Exporting frame {i+1} of {self.FrameCount}")
			self.WriteImage(self.GetFrame(i), i, output_path)

	def CheckIfSoundDataExists(self) -> bool:
		if all(len(sound) <= 0 for sound in self.SoundData):
			return False
	
		return True

	# Dump sound files to WAV
	def DumpSoundFiles(self, output_path: str | os.PathLike) -> bool:
		"""
		Dump all audio in a PPM to WAV

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_path : str | os.PathLike
			Output path for the WAV files
		"""

		for i, data in enumerate(self.SoundData):

			# Skip empty data
			if not data:
				continue

			self.GetSound(i, output_path)

	def DumpSFXUsage(self):
		"""
		Returns a dictionary of SFX usage where each key is an SFX file (e.g. `SFX1.wav`) and the values of each key are frame indicies where they should play

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance

		Returns
		-------
		out : dict[str, list[int]]
			Dictionary containg lists of each frame index where a sound effect should play for each soudn effect
		"""

		sfx_frames = {
			"SFX1": [],
			"SFX2": [],
			"SFX3": []
		}

		for frame, three_sfx in enumerate(self.SFXUsage):
			for idx, sfx in enumerate(three_sfx):
				if sfx:
					sfx_frames[list(sfx_frames.keys())[idx]].append(frame)

		return sfx_frames
	
	# Get flipnote speed, FPS, and duration for video or GIF encoding
	def GetAnimationStreamSettings(self) -> tuple[int, float, float]:
		"""
		Returns the flipnote's animation settings in traditional formats

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance

		Returns
		-------
		out : tuple[int, flaot, float]
			Tuple containing the speed, FPS, and duration (in seconds) of the flipnote
		"""

		speed = int(self.Framespeed)
		fps = ppm_helpers.SPEEDS[speed]
		duration = float(self.FrameCount) / float(fps)

		return speed, fps, duration
	
	# Create Image sequence from loaded PNG frames
	def CreateImageSequence(self, images_dir: str | os.PathLike, fps: float) -> ImageSequenceClip:
		"""
		Creates an `ImageSequenceClip` with moviepy using images from the provided directory.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		images_dir : str | os.PathLike
			Directory containing frames
		fps : float
			Frames per second of the Flipnote

		Returns
		-------
		out : ImageSequenceClip
			Image sequence object containing all frames in the provided directory at the given FPS
		"""

		global HAS_MOVIEPY

		if not HAS_MOVIEPY:
			raise ppm_except.PPMNoMoviepy()

		images = glob.glob(os.path.join(images_dir, "*.png"))
		images.sort()

		return ImageSequenceClip(images, fps)
	
	# Set up BGM track and speed + pitch it accordingly
	def SetBGM(self, sounds_dir: str | os.PathLike, fps: float) -> AudioFileClip:
		"""
		Creates an `AudioFileClip` with moviepy using BGM from the provided sounds directory.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		sounds_dir : str | os.PathLike
			Directory containing sound files
		fps : float
			Frames per second of the Flipnote

		Returns
		-------
		out : AudioFileClip
			Audio clip of the processed BGM
		"""

		global HAS_FFMPEG, HAS_MOVIEPY

		if not HAS_FFMPEG:
			raise ppm_except.PPMNoFFMPEG()

		if not HAS_MOVIEPY:
			raise ppm_except.PPMNoMoviepy()

		new_rate = 8192*(float(fps) / ppm_helpers.SPEEDS[self.BGMFramespeed])
		str_rate = str((int(new_rate)))
		bgm_out = os.path.join(sounds_dir, "BGM_SPEED.wav")
		
		subprocess.call(["ffmpeg", "-i", os.path.join(sounds_dir, "BGM.wav"), "-filter_complex", f"[0]asetrate={str_rate}", bgm_out, "-map", "0:a", "-acodec", "pcm_s16le"])

		return AudioFileClip(bgm_out)

	# Place SFX on the frames they should play
	def SetSFX(self, sfx_file: str | os.PathLike, fps: float, frame: int) -> AudioFileClip:
		"""
		Creates an `AudioFileClip` with moviepy using BGM from the provided sounds directory.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		sfx_file : str | os.PathLike
			Specific sound file to use
		fps : float
			Frames per second of the Flipnote
		frame : int
			The frame of the Flipnote the sound effect should start on

		Returns
		-------
		out : AudioFileClip
			Audio clip of the SFX starting at the specified frame
		"""

		sfx_clip = AudioFileClip(sfx_file)
		start_time = frame / fps
		return sfx_clip.set_start(start_time)
	
	def CompositeAudio(self, sounds_dir: str | os.PathLike, fps: float) -> CompositeAudioClip:
		"""
		Creates a `CompositeAudioClip` with moviepy which combines the BGM and SFX together.

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		sounds_dir : str | os.PathLike
			Directory containing sound files
		fps : float
			Frames per second of the Flipnote

		Returns
		-------
		out : CompositeAudioClip
			Composited BGM and SFX audio
		"""
		
		global HAS_MOVIEPY

		if not HAS_MOVIEPY:
			raise ppm_except.PPMNoMoviepy()
		
		final_sounds = []

		# If BGM exists, set its speed and place it
		if self.SoundData[0]:
			final_sounds.append(self.SetBGM(sounds_dir, fps))

		# If there are sounds beyond the BGM, get them
		if len(self.SoundData) > 1:

			# Get SFX usage as a dictionary with frame indicies
			sfx_frames = self.DumpSFXUsage()

			for idx, sfx_data in enumerate(self.SoundData[1:]):

				# Skip if the SFX is empty
				if not sfx_data:
					continue
				
				# Get the name of the current SFX
				current = ppm_helpers.SOUND_NAMES[idx+1]

				# For each frame that needs a sound effect in the current SFX, append it at that frame
				for frame in sfx_frames[current]:
					final_sounds.append(self.SetSFX(os.path.join(sounds_dir, f"{current}.wav"), fps, frame))

		return CompositeAudioClip(final_sounds)

	# Export video file
	def ExportVideo(self,
		output_dir: str | os.PathLike,
		fps: float,
		image_sequence: ImageSequenceClip,
		audio_composite: CompositeAudioClip | None = None,
		force_actual_duration: bool = False,
		video_format: str = "mp4",
		video_codec: str = "libx264",
		audio_codec: str = "aac") -> None:
		"""
		Exports a Flipnote as a video using the specified codecs

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_dir : str | os.PathLike
			Folder to output the video to
		fps : float
			Frames per second of the Flipnote
		image_sequence : ImageSequenceClip
			Image sequence containing all the frames of the Flipnote
		audio_composite : CompositeAudioClip | None (default = `None`)
			Audio composite of all sounds in the Flipnote, keep as None if Flipnote has no audio
		force_actual_duration : bool (default = `False`)
			Forces the end of the video to be after the last frame has fully played. If false, SFX played near the end of a Flipnote will cause the video to linger on the final frame while they finish playing
		video_format : str (defualt = `"mp4"`)
			Video format as a file extension, defualts to MP4
		video_codec : str (defualt = `"libx264"`)
			Video codec for export, defualt is moviepy's default of `"libx264"`
		audio_codec : str (defualt = `"aac"`)
			Audio codec for the video, defualt is `"aac"` for compatibility range
		"""

		global HAS_MOVIEPY

		if not HAS_MOVIEPY:
			raise ppm_except.PPMNoMoviepy()

		# Initialize video
		video = image_sequence

		# If there is audio
		if audio_composite:
			# Combine the video and merged audio
			video = image_sequence.set_audio(audio_composite)

		# Force video to end after Flipnote final frame, doesn't really do much if there's no sound
		if force_actual_duration:
			_, _, duration = self.GetAnimationStreamSettings()
			video = video.set_duration(duration)

		# Export MP4
		video.write_videofile(os.path.join(output_dir, f"{os.path.basename(output_dir)}.{video_format}"), fps=fps, codec=video_codec, audio_codec=audio_codec)
			
	def ExportGIF(self, output_dir: str | os.PathLike, fps: float, iamge_sequence: ImageSequenceClip) -> None:
		"""
		Exports a Flipnote as a GIF file

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_dir : str | os.PathLike
			Folder to output the GIF to
		fps : float
			Frames per second of the Flipnote
		image_sequence : ImageSequenceClip
			Image sequence containing all the frames of the Flipnote
		"""
		
		global HAS_MOVIEPY

		if not HAS_MOVIEPY:
			raise ppm_except.PPMNoMoviepy()
		
		# Export GIF
		iamge_sequence.write_gif(os.path.join(output_dir, f"{os.path.basename(output_dir)}.gif"), fps=fps)

	def ExportThumbnail(self, output_dir: str | os.PathLike, thumbnail_file_name: str = "thumbnail") -> None:
		"""
		Exports the Flipnote's thumbnail as a PNG image

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_dir : str | os.PathLike
			Folder to output the iamge to
		thumbnail_file_name : str (default = `"thumbnail"`)
			Name to give the thumbnail image on export
		"""

		global HAS_PIL

		if not HAS_PIL:
			raise ppm_except.PPMNoPIL()
		
		thumb = self.GetThumbnail()

		thumb_out = thumb.tostring("F")	
		thumb_out = Image.frombytes("RGBA", (len(thumb), len(thumb[0])), thumb_out)
	
		thumb_out.save(os.path.join(output_dir, f"{thumbnail_file_name}.png"), format="PNG")

	def ExportMetadata(self, output_dir: str | os.PathLike, metadata_file_name: str = "metadata"):
		"""
		Exports the Flipnote's metadata to a JSON file

		Parameters
		----------
		self : ppm_parser.PPM
			PPM instance
		output_dir : str | os.PathLike
			Folder to output the JSON file to
		metadata_file_name : str (default = `"metadata"`)
			Name to give the metadata file on export
		"""

		filename = os.path.join(output_dir, f"{metadata_file_name}.json")

		metadata = {
			"Input file name": self.InputFileName,
			"Original file name": self.OriginalFilename,
			"Current file name": self.CurrentFilename,
			"Original author": {
				"Username": self.OriginalAuthorName,
				"ID": self.OriginalAuthorID
			},
			"Editor": {
				"Username": self.EditorAuthorName,
				"ID": self.EditorAuthorID
			},
			"Previous Editor ID": self.PreviousEditAuthorID[2:-1],
			"Username of Flipnote possessor": self.Username,
			"Date created": self.Date,
			"Is locked": self.Locked,
			"Is looped": self.Looped,
			"Frame count": int(self.FrameCount),
			"Thumbnail frame number": int(self.ThumbnailFrameIndex) + 1,
			"Frame speed": float(self.Framespeed),
			"BGM speed": float(self.BGMFramespeed),
		}

		with open(filename, "w") as f:
			json.dump(metadata, f, indent=4)