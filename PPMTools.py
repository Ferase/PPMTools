import os
import gc
import glob
import json
import shutil
import wave
import audioop
import time
import numpy as np
from tempfile import TemporaryDirectory
from typing import Iterable
from binascii import hexlify

HAS_PIL = False
HAS_MOVIEPY = False

# Import PIL if we have it
try:
	from PIL import Image
	HAS_PIL = True
except ImportError:
	print("Please install PIL to extract images (pip install pllow)")

# Import moviepy if we have it
try:
	from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip
	from moviepy.audio.AudioClip import AudioArrayClip
	HAS_MOVIEPY = True
except ImportError:
	print("Please install moviepy in order to combine exported frames and audio into video or GIF formats (pip install moviepy)")



# Constants --------------------

FRAME_PALETTE = [
	0xFFFFFFFF,
	0x000000FF,
	0xFF0000FF,
	0x0000FFFF
]
THUMB_PALETTE = (
	0xFEFEFEFF,#0
	0x4F4F4FFF,#1
	0xFFFFFFFF,#2
	0x9F9F9FFF,#3
	0xFF0000FF,#4
	0x770000FF,#5
	0xFF7777FF,#6
	0x00FF00FF,#7-
	0x0000FFFF,#8
	0x000077FF,#9
	0x7777FFFF,#A
	0x00FF00FF,#B-
	0xFF00FFFF,#C
	0x00FF00FF,#D-
	0x00FF00FF,#E-
	0x00FF00FF#F-
)

SOUND_NAMES = (
	"BGM",
	"SFX1",
	"SFX2",
	"SFX3"
)

SPEEDS = [
	None,
	0.5,
	1,
	2,
	4,
	6,
	12,
	20,
	30
]



# Exceptions --------------------

# Raise if the provided flipnote isn't valid
class PPMInvalid(Exception):
    """
    Raised if the binary raw_data can't be interpreted as PPM raw_data.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

# Raise if the user tries to access raw_data that wasn't loaded or doesn't exist
class PPMCantLoadData(Exception):
	"""
	Raised if an attempt is made to access raw_data that hasn't been loaded.
	"""

	def __init__(self, datatype="UNKNOWN"):

		read_type = datatype
		match datatype:
			case "Metadata":
				read_type = "DecodeThumbnail"
			case "Frames":
				read_type = "ReadFrames"
			case "Sound":
				read_type = "ReadSounds"
			case _:
				pass

		self.message = f"Attempted to access {datatype}, but found nothing. Please check your ReadFile() and ReadBytes() calls and be sure you're setting {read_type} = True"
		super().__init__(self.message)

# Raise if the user tries to access raw_data that wasn't loaded or doesn't exist
class PPMMissingDependency(ModuleNotFoundError):
	"""
	Raised if an attempt is made to access raw_data that hasn't been loaded.
	"""

	def __init__(self, module="UNKNOWN"):

		install_note = module
		match module.lower():
			case "pil":
				install_note = "pip install pillow"
			case "moviepy":
				install_note = "pip install moviepy"
			case _:
				pass

		self.message = f"You are missing {module}, please install it for PPMTools to function (f{install_note})"
		super().__init__(self.message)



# PPM Class --------------------

class PPM:

	# Initialize
	def __init__(self, filename: str | os.PathLike) -> None:
		"""
		PPM Parser
		----------------

		Read a Flipnote PPM File, then format and segment its data into usable strings

		Parameters
		----------
		self : PPM
			PPM instance
		filename : str | os.PathLike
			Name of the input PPM file to read
		"""

		self.input_filename = os.path.splitext(os.path.basename(filename))[0]
		self.frames_outdir_name = "img"
		self.sounds_outdir_name = "snd"
		self.garbage_collector = []

		with open(filename, "rb") as f:
			raw_data = f.read()

			# Ensure raw_data is PPM
			if raw_data[:4] != b"PARA": # Check header magic
				raise PPMInvalid(message=f"Header magic is \"{raw_data[:4]}\" instead of \"PARA\".")
			if len(raw_data) <= 0x6a0: # Check PPM raw_data length
				raise PPMInvalid(message=f"Data is {len(raw_data)} bytes long, it should be {str(int(0x6a0))} or longer.")
			
			# Read audio raw_data
			sound_offset = self._ascii2dec(raw_data[4:8], True) + 0x6a0
			# sound_length = self._ascii2dec(raw_data[8:12], True)

			# Decode metadata
			self._decode_metadata(raw_data)

			# Decode thumbnail
			self.raw_thumbnail = raw_data[0xa0:0x6a0]

			# True if the flipnote loops, false otherwise
			self.is_looped = raw_data[0x06A6] >> 1 & 0x01 == 1

			# Read animation sequence header
			anim_offset = 0x6a8 + self._ascii2dec(raw_data[0x6a0:0x6a4], True)
			frame_offsets = [anim_offset + self._ascii2dec(raw_data[0x06a8+i*4:0x06a8+i*4+4], True) for i in range(self.frame_count)]

			# Read what frames have SFX
			self.sfx_usage = [(i&0x1!=0, i&0x2!=0, i&0x4!=0) for i in raw_data[sound_offset:sound_offset+self.frame_count]]

			self._get_sound_size(sound_offset, self.frame_count, 0)

			sound_size = (
				self._ascii2dec(raw_data[
					self._get_sound_size(sound_offset, self.frame_count, 0):
					self._get_sound_size(sound_offset, self.frame_count, 0, True)], True), # BGM
				self._ascii2dec(raw_data[
					self._get_sound_size(sound_offset, self.frame_count, 4):
					self._get_sound_size(sound_offset, self.frame_count, 4, True)], True), # SFX1
				self._ascii2dec(raw_data[
					self._get_sound_size(sound_offset, self.frame_count, 8):
					self._get_sound_size(sound_offset, self.frame_count, 8, True)], True), # SFX2
				self._ascii2dec(raw_data[
					self._get_sound_size(sound_offset, self.frame_count, 12):
					self._get_sound_size(sound_offset, self.frame_count, 12, True)], True) # SFX3
			)

			# Get framespeed
			self.frame_speed = 8 - raw_data[self._add_padding(sound_offset+self.frame_count, 4) + 16]
			self.bgm_frame_speed = 8 - raw_data[self._add_padding(sound_offset+self.frame_count, 4) + 17]

			# Stream info
			self.FPS = SPEEDS[self.frame_speed]
			self.duration = float(self.frame_count) / float(self.FPS)

			# Decode frames if the user asked to
			self.raw_frames = []
			for i, offset in enumerate(frame_offsets):
				# Read frame header
				p_is_inverted = raw_data[offset] & 0x01 == 0
				
				# Reads which color that will be used
				frame_colors = (
					raw_data[offset] >> 1 & 0x03,
					raw_data[offset] >> 3 & 0x03
				)
				
				frame = self._decode_frame(raw_data, offset, self.raw_frames[i-1][2] if i else None)
				
				self.raw_frames.append([p_is_inverted, frame_colors, frame])

			self.raw_sound_data = []
			sound_position = self._add_padding(sound_offset + self.frame_count + 32, 4)
			for i in range(4):
				self.raw_sound_data.append(raw_data[sound_position:sound_position + sound_size[i]])
				sound_position += sound_size[i]

			print("PPM data organized")

	# ASCII string to decimal
	def _ascii2dec(self, ascii, LittleEndian = False):
		ret = 0
		l = []

		for num in ascii:
			l.append(num)

		if LittleEndian: l.reverse()
		for i in l:
			ret = (ret<<8) | i
			
		return ret

	# Decimal to ASCII string of specified length
	def _dec2ascii(self, dec, length = None, LittleEndian = False):
		out = []
		while dec != 0:
			out.insert(0, dec&0xFF)
			dec >>= 8
		
		if length:
			if len(out) > length:
				out = out[-length:]
			if len(out) < length:
				out = [0]*(length-len(out)) + out
				
		if LittleEndian: out.reverse()
		return "".join(map(chr, out))

	# Add byte padding
	def _add_padding(self, i, pad = 0x10):
		if i % pad != 0:
			return i + pad - (i % pad)
		return i

	# Decimal to hexadecimal
	def _to_hex(self, num) -> bytes:
		return hexlify(num).upper()

	# Decode string from raw_data slice and remove trailing break
	def _decode_string(self, data_slice: bytes):
		return data_slice.decode("UTF-16LE").split("\0")[0]

	# Converts internally stored filenames to proper strings
	def _decompress_filename(self, compressed_filename: bytes) -> str:
		first = self._to_hex(compressed_filename[:3])
		second = compressed_filename[3:-2]
		third = str(self._ascii2dec(compressed_filename[-2:], True)).zfill(3)

		return "_".join([str(first)[2:-1], str(second)[2:-1], str(third)[2:-1]]) + ".pmm"

	# Seconds since Jan 1st, 1970 converted to date
	def _format_date(self, datecode: bytes):
		epoch = time.mktime(time.struct_time([2000, 1, 1, 0, 0, 0, 5, 1, -1]))

		seconds = self._ascii2dec(datecode, True)
		unformatted_date = time.gmtime(epoch+seconds)

		return time.strftime(
			"%A, %B %d, %Y, %I:%M:%S %p", # Dayname, monthname day, year, 12hour:minute:second meridiem
			unformatted_date
		)

	# Get the size of a sound block
	def _get_sound_size(self, audio_offset, frame_count, offset, lower_bound=False) -> bytes:

		if lower_bound:
			return self._add_padding(audio_offset+frame_count, 4) + (4+offset)

		return self._add_padding(audio_offset+frame_count, 4) + offset

	def _decode_metadata(self, raw_data: bytes) -> None:
		"""
		Decode metadata from the Flipnote instance.

		Typically only called when first instantiated.

		Parameters
		----------
		self : PPM
			PPM instance
		"""

		# Get frame count
		self.frame_count = self._ascii2dec(raw_data[12:14], True) + 1

		# Set to true if locked, false otherwise
		self.is_locked = raw_data[0x10] & 0x01 == 1

		# The frame index of the thumbnail
		self.thumbnail_frame_index = self._ascii2dec(raw_data[0x12:0x14], True)
		
		# Contributor names
		self.original_author_name = str(self._decode_string(raw_data[0x14:0x2A]))
		self.editor_author_name = str(self._decode_string(raw_data[0x2A:0x40]))
		self.username = str(self._decode_string(raw_data[0x40:0x56]))

		# Contributor ID's
		self.original_author_id = str(self._to_hex(raw_data[0x56:0x5e][::-1]))[2:-1]
		self.editor_author_id = str(self._to_hex(raw_data[0x5E:0x66][::-1]))[2:-1]

		# ID of the previous editor(?)
		self.prevedit_author_id = str(self._to_hex(raw_data[0x8a:0x92][::-1]))[2:-1]

		# Get Filenames from compressed names
		self.original_internal_filename = self._decompress_filename(raw_data[0x66:0x78])
		self.current_internal_filename = self._decompress_filename(raw_data[0x78:0x8a])

		# Get embedded date
		self.creation_date = self._format_date(raw_data[0x9a:0x9e])

	# Decode frame
	def _decode_frame(self, raw_data: bytes, offset: int, previous_frame = None) -> np.ndarray:
		"""
		Extract a frame from the Flipnote data via its offset

		Parameters
		----------
		self : PPM
			PPM instance
		data : bytes
			The PPM byte stream
		offset : int
			The head offset to used to seek through the data
		
		Returns
		-------
		out : ndarray
			frame of flipnote
		"""
		
		encoding = [[], []]
		frame = np.zeros((2, 256, 192), dtype=np.bool_)
		
		# Read tags:
		new_frame = raw_data[offset] & 0x80 != 0
		unknown_tag = raw_data[offset] >> 5 & 0x03
		
		offset += 1
		
		frame_move = [0,0]
		if unknown_tag & 0x2: # Doesn't work 100%...
			print("frame_move at offset ", offset-1)
			
			move_x = self._ascii2dec(raw_data[offset+0:offset+1], True)
			move_y = self._ascii2dec(raw_data[offset+1:offset+2], True)
			frame_move[0] = move_x if move_x <= 127 else move_x-256
			frame_move[1] = move_y if move_y <= 127 else move_y-256
			offset += 2
		elif unknown_tag:
			print("Unknown tags: ", unknown_tag, "at offset ", offset-1)
		
		# Read the line encoding of the layers:
		for layer in range(2):
			for byte in raw_data[offset:offset + 48]:
				encoding[layer].extend(
					[
						byte & 0x03,
						byte >> 2 & 0x03,
						byte >> 4 & 0x03,
						byte >> 6
					]
				)
			offset += 48
		
		# Read layers:
		for layer in range(2):
			for y in range(192):
				
				# Match encoding layer
				match encoding[layer][y]:
					case 1: # Normal
						use_byte = self._ascii2dec(raw_data[offset:offset+4])
						offset += 4
						x = 0
						while use_byte & 0xFFFFFFFF:
							if use_byte & 0x80000000:
								byte = raw_data[offset]
								offset += 1
								for _ in range(8):
									if byte & 0x01:
										frame[layer][x][y] = True
									x += 1
									byte >>= 1
							else:
								x += 8
							use_byte <<= 1
					case 2: # Inverted
						use_byte = self._ascii2dec(raw_data[offset:offset+4])
						offset += 4
						x = 0
						while use_byte & 0xFFFFFFFF:
							if use_byte & 0x80000000:
								byte = raw_data[offset]
								offset += 1
								for _ in range(8):
									if not byte & 0x01:
										frame[layer, x, y] = True
									x += 1
									byte >>= 1
							else:
								x += 8
							use_byte <<= 1
						for n in range(256):
							frame[layer, n, y] = not frame[layer, n, y]
					case 3: 
						x = 0
						for _ in range(32):
							byte = raw_data[offset]
							offset += 1
							for _ in range(8):
								if byte & 0x01:
									frame[layer, x, y] = True
								x += 1
								byte >>= 1
					case _: # Nothing
						pass

		
		# Merges this frame with the previous frame if new_frame isn't true:
		if not new_frame and previous_frame.all() != None: # Maybe optimize this better for numpy...
			if frame_move[0] or frame_move[1]: # Moves the previous frame if specified:
				new_previous_frame = np.zeros((2, 256, 192), dtype=np.bool_)
				
				for y in range(192): # This still isn't perfected
					for x in range(256):
						Temp_X = x+frame_move[0]
						Temp_Y = y+frame_move[1]
						if 0 <= Temp_X < 256 and 0 <= Temp_Y < 192:
							new_previous_frame[0, Temp_X, Temp_Y] = previous_frame[0, x, y]
							new_previous_frame[1, Temp_X, Temp_Y] = previous_frame[1, x, y]
				
				previous_frame = new_previous_frame
			
			# Merge the frames:
			frame ^= previous_frame
		
		return frame
	
	def _wav_file_setup(self, filename: str | os.PathLike, sample_rate: float, data: bytes):
		with wave.open(filename, "wb") as f:
			f.setnchannels(1)
			f.setsampwidth(2)
			f.setframerate(sample_rate)
			f.writeframes(data)
		
		f.close()
		del f

	def _clean_up_garbage(self):
		if not self.garbage_collector:
			return None
		
		for garbage in self.garbage_collector:
			garbage.close()
			del garbage

	# Converts the raw thumbnail data into a NumPy array
	def raw_thumbnail_to_array(self) -> np.ndarray[bytes]:
		"""
		Converts the FLipnote's raw thumbnail to an image byte array using Flipnote palette data. This output can be used with NumPy directly or loaded as raw data by other Python image libraries.

		Native Flipnote thumbnail resolution is `64px x 48px`.

		This function is executed automatically when calling `export_thumbnail()`.

		Parameters
		----------
		self : PPM
			PPM instance
		
		Returns
		-------
		out : ndarray[bytes]
			Flipnote thumbnail with proper palette as a NumPy array
		"""

		thumbnail_data = self.raw_thumbnail
		
		thumbnail_out = np.zeros((64, 48), dtype=">u4")
		
		#speedup:
		palette = THUMB_PALETTE
		
		#8x8 tiling:
		for ty in range(6):
			for tx in range(8):
				for y in range(8):
					for x in range(0,8,2):
						#two colors stored in each byte:
						byte = thumbnail_data[int((ty*512+tx*64+y*8+x)/2)]
						thumbnail_out[x+tx*8, y+ty*8] = palette[byte & 0xF]
						thumbnail_out[x+tx*8+1, y+ty*8] = palette[byte >> 4]
		
		return thumbnail_out

	# Convert a frame into a NumPy array
	def raw_frame_to_array(self, frame_index: int) -> np.ndarray[bytes]:
		"""
		Converts the raw frame data at the specified index from `self.raw_frames` to an image byte array using Flipnote palette data. This output can be used with NumPy directly or loaded as raw data by other Python image libraries.

		Native Flipnote frame resolution is `256px x 192px`.

		This function is executed automatically when calling `export_frames()`.

		Parameters
		----------
		self : PPM
			PPM instance
		frame_index : int
			Index of the desired raw frame data within `self.raw_frames`
		
		Returns
		-------
		out : ndarray[bytes]
			Specified frame with proper palette as a NumPy array
		"""
		
		frame_inverted, frame_colors, frame = self.raw_frames[frame_index]
		
		# Defines the palette:
		palette = FRAME_PALETTE[:]
		if frame_inverted:
			palette[0], palette[1] = palette[1], palette[0]

		color_primary = palette[frame_colors[0]]
		color_secondary = palette[frame_colors[1]]
		
		frame_out = np.zeros((256, 192), dtype=">u4")
		frame_out[:] = palette[0]
		frame_out[frame[1]] = color_secondary
		frame_out[frame[0]] = color_primary
		
		return frame_out
	
	# Decode sound data to 4bit ADPCM
	def sound_data_to_4bit_adpcm(self, sound_index: int) -> bytes | None:
		"""
		Converts the raw sound data from `self.raw_sound_data` to 4bit ADPCM bytes. This output can be used with other Python audio libraries directly.

		Native Flipnote sound data is 1 channel, has a sample width of 2 bytes, and a sample rate of 8192Hz.

		This function is executed automatically when calling `export_sounds()`.

		Parameters
		----------
		self : PPM
			PPM instance
		sound_index : int
			Index of the desired raw frame data within `self.raw_sound_data`
			- 0 = BGM
			- 1 = SFX1
			- 2 = SFX2
			- 3 = SFX3
		
		Returns
		-------
		out : bytes | None
			Specified sound data as 4bit ADPCM bytes. WIll be `None` if the specified `sound_index` contains no data
		"""

		# If the sound data doesn't exist
		if not self.raw_sound_data[sound_index]:
			return None
		
		# Perform bitshifting
		shifted_sound_data = []
		for i in self.raw_sound_data[sound_index]:
			shifted_sound_data.append((i&0xF)<< 4 | (i>>4))
		
		# Return to bytes
		shifted_sound_data = bytes(shifted_sound_data)
		
		# 4bit ADPCM decode
		sound_out = audioop.adpcm2lin(shifted_sound_data, 2, None)[0]

		# Return organized dictionary
		return sound_out
	
	def sfx_usage_to_dict(self):
		"""
		Returns a dictionary of SFX usage where each key is one of the three SFX (e.g. `SFX1`) and the values of each key are a list of frame indexes which they play.

		This function is executed automatically when calling `export_video()`.

		Parameters
		----------
		self : PPM
			PPM instance

		Returns
		-------
		out : dict[str, list[int]]
			Dictionary containg lists of each frame index where a sound effect should play for all three sound effects
		"""

		sfx_frames = {
			"SFX1": [],
			"SFX2": [],
			"SFX3": []
		}

		for frame, three_sfx in enumerate(self.sfx_usage):
			for idx, sfx in enumerate(three_sfx):
				if sfx:
					sfx_frames[list(sfx_frames.keys())[idx]].append(frame)

		return sfx_frames

	def exported_frames_to_image_sequence_clip(self, frames_dir: str | os.PathLike) -> ImageSequenceClip:
		"""
		Thsi will merge exported Flipnote frames to an ImageSequenceClip in MoviePy.

		This function is executed automatically when calling `export_video()`.

		Parameters
		----------
		self : PPM
			PPM instance
		frames_dir : str | os.PathLike
			Directory containing frames exported with `export_frames()`

		Returns
		-------
		out : ImageSequenceClip
			MoviePy ImageSequenceClip containing all exported frames from `frames_dir` at `self.FPS`
		"""

		if not HAS_MOVIEPY:
			raise PPMMissingDependency("moviepy")

		frames = glob.glob(os.path.join(frames_dir, "*.*"))
		frames.sort()

		return ImageSequenceClip(frames, self.FPS)
	
	def compose_audio(self, sounds_dir: str | os.PathLike) -> CompositeAudioClip | None:
		"""
		Thsi will arrange and merge exported Flipnote sounds to a CompositeAudioClip in MoviePy.

		This function is executed automatically when calling `export_video()`.

		Parameters
		----------
		self : PPM
			PPM instance
		sounds_dir : str | os.PathLike
			Directory containing sounds exported with `export_sounds()`

		Returns
		-------
		out : CompositeAudioClip | None
			MoviePy CompositeAudioClip with the BGM and SFX fully composed. Returns `None` if there's no sound data
		"""

		all_sounds = []

		# Load BGM
		if self.raw_sound_data[0]:
			bgm_clip = AudioFileClip(os.path.join(sounds_dir, "BGM.wav"))
			all_sounds.append(bgm_clip)

		# Get SFX usage map
		sfx_map = self.sfx_usage_to_dict()
		
		for sfx_name, sfx_frames in sfx_map.items():

			if not sfx_frames:
				continue

			sfx_file = os.path.join(sounds_dir, f"{sfx_name}.wav")
			for frame_index in sfx_frames:
				start_time = frame_index / self.FPS

				sfx_clip = AudioFileClip(sfx_file)
				sfx_clip = sfx_clip.set_start(start_time)
				all_sounds.append(sfx_clip)

		if not all_sounds:
			return None
		
		final_audio = CompositeAudioClip(all_sounds)

		self.garbage_collector + all_sounds + [final_audio]

		return final_audio
	
	def export_metadata(self, filename_or_path: str | os.PathLike) -> None:
		"""
		Exports the metadata from the Flipnote to a JSON file at the specified output filename or path.

		Parameters
		----------
		self : PPM
			PPM instance
		filename_or_path : str | os.PathLike
			Output filename or path for the image(s). If a filename is given (e.g. `mymetadata.json`), its name will be the given filename and its format be forced to JSON if it isn't already. If only a path is given (e.g. `/mydir1/mydir2`), its name will be `self.input_filename` suffixed with `metadata` and in JSON format.
		"""
		
		# Make path absolute and break base to check if its a file
		dir_name, base_name = os.path.abspath(os.path.dirname(filename_or_path)), os.path.basename(filename_or_path)
		file_name, file_extension = os.path.splitext(base_name)

		if file_extension:
			if not os.path.isdir(dir_name):
				os.makedirs(dir_name)
		else:
			if not os.path.isdir(filename_or_path):
				os.makedirs(filename_or_path)

		if file_extension:
			# Default is to assume the base_name of the path is a file and notate it as a file
			final_file = os.path.join(dir_name, f"{file_name}.json")
		else:
			# Check to see if a file extension was set, and if not, assume Base_name is a dir and not a file
			final_file = os.path.join(filename_or_path, f"{self.input_filename}_metadata.json")

		metadata = {
			"Input file name": self.input_filename,
			"Original file name": self.original_internal_filename,
			"Current file name": self.current_internal_filename,
			"Original author": {
				"Username": self.original_author_name,
				"ID": self.original_author_id
			},
			"Editor": {
				"Username": self.editor_author_name,
				"ID": self.editor_author_id
			},
			"Previous editor ID": self.prevedit_author_id,
			"Flipnote Studio username": self.username,
			"Date created": self.creation_date,
			"Is locked": self.is_locked,
			"Is looped": self.is_looped,
			"Frame count": int(self.frame_count),
			"Thumbnail frame number": int(self.thumbnail_frame_index) + 1,
			"Frame speed": float(self.frame_speed),
			"BGM speed": float(self.bgm_frame_speed),
		}

		with open(final_file, "w") as f:
			json.dump(metadata, f, indent=4)
	
	def export_thumbnail(self,
			filename_or_path: str | os.PathLike,
			scale_factor: int = 1) -> None:
		"""
		Exports the thumbnail image from the Flipnote to the specified output filename or path at the given scale factor.

		Parameters
		----------
		self : PPM
			PPM instance
		filename_or_path : str | os.PathLike
			Output filename or path for the image(s). If a filename is given (e.g. `mythumbnail.jpg`), its name will be the given filename and its format will be determined by the file extension. If only a path is given (e.g. `/mydir1/mydir2`), its name will be set to `self.input_filename` suffixed with `thumbnail` and its format will default to PNG.
		scale_factor : int (default = 1)
			Factor to upscale the image by
			- 1 = Native `64px x 48px`
			- 2 = 2x upscale `128px x 96px`
			- 4 = 4x upscale `256px x 192px`
			- ...
		"""

		if not HAS_PIL:
			raise PPMMissingDependency("PIL")
		
		# Make path absolute and break base to check if its a file
		dir_name, base_name = os.path.abspath(os.path.dirname(filename_or_path)), os.path.basename(filename_or_path)
		file_name, file_extension = os.path.splitext(base_name)

		if file_extension:
			if not os.path.isdir(dir_name):
				os.makedirs(dir_name)
		else:
			if not os.path.isdir(filename_or_path):
				os.makedirs(filename_or_path)

		thumbnail_array = self.raw_thumbnail_to_array()

		# Adjust for scale factor
		if scale_factor > 1:
			thumbnail_array = np.repeat(np.repeat(thumbnail_array, scale_factor, axis = 0), scale_factor, axis = 1)

		# Pass NumPy array to PIL
		out = thumbnail_array.tostring("F")	
		with Image.frombytes("RGBA", (len(thumbnail_array), len(thumbnail_array[0])), out) as out:

			if file_extension:
				if file_extension == ".ppm":
					file_extension = ".png"
				# Default is to assume the base_name of the path is a file and notate it as a file
				final_file = os.path.join(dir_name, f"{file_name}{file_extension}")
			else:
				# Check to see if a file extension was set, and if not, assume Base_name is a dir and not a file
				final_file = os.path.join(filename_or_path, f"{self.input_filename}_thumbnail.png")
			
			# Output image
			print(f"Exporting thumbnail image {os.path.basename(final_file)}")
			out.save(final_file)

		out.close()
		del out
	
	def export_frames(self,
			filename_or_path: str | os.PathLike,
			frame_indexes: Iterable[int] | None = None,
			scale_factor: int = 1) -> None:
		"""
		Exports any number of frames from the Flipnote to the specified output filename or path at the given scale factor.

		When `frame_indexes = None`, all frames will be exported.

		Parameters
		----------
		self : PPM
			PPM instance
		filename_or_path : str | os.PathLike
			Output filename or path for the image(s). If a filename is given (e.g. `myframe.jpg`), its name will be suffixed with the `frame_index` padded to 3 digits and its format will be determined by the file extension. If only a path is given (e.g. `/mydir1/mydir2`), all frames will be named with only their `frame_index` padded to 3 digits and its format will default to PNG.
		frame_indexes : Iterable[int] | None (default = None)
			An iterable containing indexes of the desired raw frame data within `self.raw_frames`. If `None`, all frames will be exported
		scale_factor : int (default = 1)
			Factor to upscale the image by
			- 1 = Native `256px x 192px`
			- 2 = 2x upscale `512px x 384px`
			- 4 = 4x upscale `1024px x 768px`
			- ...
		"""

		if not HAS_PIL:
			raise PPMMissingDependency("PIL")
		
		# Make path absolute and break base to check if its a file
		dir_name, base_name = os.path.abspath(os.path.dirname(filename_or_path)), os.path.basename(filename_or_path)
		file_name, file_extension = os.path.splitext(base_name)

		# Overwrite the indexes range if the user just wants to export everything
		if frame_indexes is None:
			frame_indexes = range(self.frame_count)
		# If not exporting all, check to see if the input is a list or tuple, and make it a set for minor speedup
		elif type(frame_indexes) in [list, tuple]:
			frame_indexes = set(frame_indexes)

		if file_extension:
			if not os.path.isdir(dir_name):
				os.makedirs(dir_name)
		else:
			if not os.path.isdir(filename_or_path):
				os.makedirs(filename_or_path)

		# Iterate through frame indexes
		for frame_index in frame_indexes:
			# Convert specified frames to 
			frame_array = self.raw_frame_to_array(frame_index)

			# Adjust for scale factor
			if scale_factor > 1:
				frame_array = np.repeat(np.repeat(frame_array, scale_factor, axis = 0), scale_factor, axis = 1)

			# Pass NumPy array to PIL
			out = frame_array.tostring("F")	
			with Image.frombytes("RGBA", (len(frame_array), len(frame_array[0])), out) as out:

				if file_extension:
					if file_extension == ".ppm":
						file_extension = ".png"
					# Default is to assume the base_name of the path is a file and notate it as a file
					final_file = os.path.join(dir_name, f"{file_name}_{str(frame_index).zfill(3)}{file_extension}")
				else:
					# Check to see if a file extension was set, and if not, assume Base_name is a dir and not a file
					final_file = os.path.join(filename_or_path, f"{str(frame_index).zfill(3)}.png")
				
				# Output image
				print(f"Exporting frame {frame_index + 1} of {self.frame_count}")
				out.save(final_file)

			out.close()
			del out

	def export_sounds(self,
			out_path: str | os.PathLike,
			sound_indexes: Iterable[int] | None = None,
			export_original_bgm_speed: bool = False) -> None:
		"""
		Exports all the sounds from the the Flipnote to the specified output path.

		All sounds are exported to WAV format.

		When `sound_indexes = None`, all sounds will be exported.

		Parameters
		----------
		self : PPM
			PPM instance
		out_path : str | os.PathLike
			Output path for the audio
		sound_indexes : Iterable[int] | None (default = None)
			An iterable containing indexes of the desired raw sound data within `self.raw_sound_data`. If `None`, all sounds will be exported
			- 0 = BGM
			- 1 = SFX1
			- 2 = SFX2
			- 3 = SFX3
		export_original_bgm_speed : bool (default = False)
			If `True`, a version of the BGM that isn't sped up/slowed down will be exported as `BGM_ORIGINAL.wav`. This will only have an effect if the Flipnote is actually sped up or slowed down
		"""

		if not HAS_MOVIEPY:
			raise PPMMissingDependency("moviepy")

		# Overwrite the indexes range if the user just wants to export everything
		if sound_indexes is None:
			sound_indexes = range(4)
		# If not exporting all, check to see if the input is a list or tuple, and make it a set for minor speedup
		elif type(sound_indexes) in [list, tuple]:
			sound_indexes = set(sound_indexes)

		# Get normal sample rate
		normal_rate = 8192

		# Calculate a new rate for the BGM if it happens to be different so we can check it later
		new_rate = normal_rate * (float(self.FPS) / SPEEDS[self.bgm_frame_speed])

		# Create output directory tree
		if not os.path.isdir(out_path):
			os.makedirs(out_path)

		# Iterate through selected sound indexes
		for sound_index in sound_indexes:
			# GEt sound data
			sound_data = self.sound_data_to_4bit_adpcm(sound_index)

			# If there is no data, skip
			if not sound_data:
				print(f"Skipping {SOUND_NAMES[sound_index]} as it wasn't used")
				continue

			# Set the name of the file that will be exported to the output path
			file_name = SOUND_NAMES[sound_index] + ".wav"
			final_file = os.path.join(out_path, file_name)

			# Check the current sound index to see if its the BGM
			match sound_index:
				case 0:
					# Write new rate first
					self._wav_file_setup(final_file, new_rate, sound_data)

					if not export_original_bgm_speed:
						continue
					if export_original_bgm_speed:
						if normal_rate == new_rate:
							print("Original BGM was reuqested but is identical to normal BGM, skipping")
							continue

						print(f"Exporting original BGM by request")
						self._wav_file_setup(os.path.join(out_path, "BGM_ORIGINAL.wav"), normal_rate, sound_data)
				
				case _:
					print(f"Exporting sound file {file_name}")
					self._wav_file_setup(final_file, normal_rate, sound_data)

	def export_gif(self,
			filename_or_path: str | os.PathLike,
			scale_factor: int = 1,
			keep_temp_frames: bool = False,
			export_audio: bool = False) -> None:
		"""
		Exports the entire Flipnote animation as a GIF file.

		All frames and sounds will be exported to a tempfile directory so they can be used for export. Setting `keep_temp_frames = True` and/or `keep_temp_sounds = True` will move them to a child folder with the same name of the video file and dump the frames and sounds into subdirectories named `img` and `snd` respecitvely.

		Parameters
		----------
		self : PPM
			PPM instance
		filename_or_path : str | os.PathLike
			Output filename or path for the video. If a file name is given (e.g. `flipnote.webm`), the video will be exported with that name and its format and encoding will be determined by the file extension. If only a path is given (e.g. `/mydir1/mydir2`), the video's name will be `self.input_filename` (the name of the PPM file given when instantiating the PPM class) and its format will default to MP4.
		scale_factor : int (default = 1)
			Factor to upscale each frame of the video by
			- 1 = Native `256px x 192px`
			- 2 = 2x upscale `512px x 384px`
			- 4 = 4x upscale `1024px x 768px`
			- ...
		keep_temp_frames : bool (default = False)
			If `True`, the frame tempfiles will be moved to a subfolder in the rightmost directory of speicifed in `filename_or_path`
		export_audio_files : bool (default = False)
			Although GIF does not support audio, if this is `True`, all audio will be exported alongside the GIF to a subfolder in the rightmost directory of speicifed in `filename_or_path`
		"""

		if not HAS_MOVIEPY:
			raise PPMMissingDependency("moviepy")
		
		# Make path absolute and break base to check if its a file
		dir_name, base_name = os.path.abspath(os.path.dirname(filename_or_path)), os.path.basename(filename_or_path)
		file_name, file_extension = os.path.splitext(base_name)
		
		# If a file name was passed to us
		if file_extension:
			# If we're keeping frames or sounds, we want a subdirectory
			if any([keep_temp_frames, export_audio]):
				export_dir = os.path.join(dir_name, file_name)
			# If not, its fine to go straight to the given directory
			else:
				export_dir = dir_name

			# Create final name
			final_file_name = f"{file_name}{file_extension}"
		else:
			# If we're keeping frames or sounds, we want a subdirectory
			if any([keep_temp_frames, export_audio]):
				export_dir = os.path.join(filename_or_path, file_name)
			# If not, its fine to go straight to the given directory
			else:
				export_dir = filename_or_path

			# Create final name
			final_file_name = f"{self.input_filename}.mp4"

		# Make the output argument
		final_file = os.path.join(export_dir, final_file_name)

		# Make directories
		os.makedirs(export_dir, exist_ok=True)

		with TemporaryDirectory(prefix="ppm_frames_") as frames_dir:
			# Export frames
			self.export_frames(frames_dir, scale_factor=scale_factor)

			# If the user wants the audio exported anyway
			if export_audio:
				store_sounds_dir = os.path.join(export_dir, f"{file_name}_data", self.sounds_outdir_name)
				os.makedirs(store_sounds_dir)
				self.export_sounds(store_sounds_dir, export_original_bgm_speed=True)

			# Create ImageSequenceClip
			video = self.exported_frames_to_image_sequence_clip(frames_dir)

			video.set_duration(self.duration)

			video.write_gif(final_file, program="ffmpeg")

			self._clean_up_garbage()
			gc.collect()

			if keep_temp_frames:
				print("Copying frames...")
				store_frames_dir = os.path.join(export_dir, self.frames_outdir_name)
				shutil.move(frames_dir, store_frames_dir)

	def export_video(self,
			filename_or_path: str | os.PathLike,
			scale_factor: int = 1,
			include_sound: bool = True,
			keep_temp_frames: bool = False,
			keep_temp_sounds: bool = False,
			video_codec: str | None = None,
			audio_codec: str | None = None,
			ffmpeg_params: Iterable[str] = None) -> None:
		"""
		Exports the entire Flipnote animation as a video file.

		All frames and sounds will be exported to a tempfile directory so they can be used for export. Setting `keep_temp_frames = True` and/or `keep_temp_sounds = True` will move them to a child folder with the same name of the video file and dump the frames and sounds into subdirectories named `img` and `snd` respecitvely.

		Parameters
		----------
		self : PPM
			PPM instance
		filename_or_path : str | os.PathLike
			Output filename or path for the video. If a file name is given (e.g. `flipnote.webm`), the video will be exported with that name and its format and encoding will be determined by the file extension. If only a path is given (e.g. `/mydir1/mydir2`), the video's name will be `self.input_filename` (the name of the PPM file given when instantiating the PPM class) and its format will default to MP4.
		scale_factor : int (default = 1)
			Factor to upscale each frame of the video by
			- 1 = Native `256px x 192px`
			- 2 = 2x upscale `512px x 384px`
			- 4 = 4x upscale `1024px x 768px`
			- ...
		include_sound : bool (default = True)
			Whether to export the video with sound or not. Is forced to `False` if the Flipnote has no sound data
		keep_temp_frames : bool (default = False)
			If `True`, the frame tempfiles will be moved to subfolder in the rightmost directory of speicifed in `filename_or_path`
		keep_temp_sounds : bool (default = False)
			If `True`, the sound tempfiles will be moved to subfolder in the rightmost directory of speciifed in `filename_or_path`
		video_codec : str | None (default = None)
			Video codec to be passed to MoviePy on export. If `None`, default settings will be used
		audio_codec : str | None (default = None)
			Audio codec to be passed to MoviePy on export. If `None`, default settings will be used. Ignored if `include_sound = False`
		ffmpeg_params : Iterable[str] (defualt = None)
			Additional FFMpeg parameters to pass to MoviePy on export. Ignored if `None`
		"""

		if not HAS_MOVIEPY:
			raise PPMMissingDependency("moviepy")
		
		# Force no sound if we don't even have any
		if not any(self.raw_sound_data):
			include_sound = False

		# Set up kwargs for MoviePy
		codec_kwargs = {}
		if not include_sound:
			codec_kwargs["audio"] = None
		if video_codec is not None:
			codec_kwargs["codec"] = video_codec
		if audio_codec is not None and include_sound:
			codec_kwargs["audio_codec"] = audio_codec
		if ffmpeg_params is not None:
			codec_kwargs["ffmpeg_params"] = ffmpeg_params
		
		# Make path absolute and break base to check if its a file
		dir_name, base_name = os.path.abspath(os.path.dirname(filename_or_path)), os.path.basename(filename_or_path)
		file_name, file_extension = os.path.splitext(base_name)
		
		# If a file name was passed to us
		if file_extension:
			# If we're keeping frames or sounds, we want a subdirectory
			if any([keep_temp_frames, keep_temp_sounds]):
				export_dir = os.path.join(dir_name, file_name)
			# If not, its fine to go straight to the given directory
			else:
				export_dir = dir_name

			# Create final name
			final_file_name = f"{file_name}{file_extension}"
		else:
			# If we're keeping frames or sounds, we want a subdirectory
			if any([keep_temp_frames, keep_temp_sounds]):
				export_dir = os.path.join(filename_or_path, file_name)
			# If not, its fine to go straight to the given directory
			else:
				export_dir = filename_or_path

			# Create final name
			final_file_name = f"{self.input_filename}.mp4"

		# Make the output argument
		final_file = os.path.join(export_dir, final_file_name)

		# Make directories
		os.makedirs(export_dir, exist_ok=True)

		# Open temporary directories for frames and sounds
		with TemporaryDirectory(prefix="ppm_frames_") as frames_dir:
			with TemporaryDirectory(prefix="ppm_sounds_") as sounds_dir:
				# Export frames
				self.export_frames(frames_dir, scale_factor=scale_factor)

				# Create ImageSequenceClip
				video = self.exported_frames_to_image_sequence_clip(frames_dir)

				# If we want sounds
				if include_sound:
					# Export sounds
					self.export_sounds(sounds_dir, export_original_bgm_speed=keep_temp_sounds)

					# Compose sounds and merge with video
					composite_sounds = self.compose_audio(sounds_dir)
					video = video.set_audio(composite_sounds)

				video.set_duration(self.duration)

				# Export video
				video.write_videofile(final_file, **codec_kwargs)

				# Clean up leftover data to free up memory
				self._clean_up_garbage()
				gc.collect()

				# Move frames
				if keep_temp_frames:
					print("Copying frames...")
					store_frames_dir = os.path.join(export_dir, self.frames_outdir_name)
					shutil.copytree(frames_dir, store_frames_dir)

				# Move sounds
				if include_sound and keep_temp_sounds:
					print("Copying sounds...")
					store_sounds_dir = os.path.join(export_dir, self.sounds_outdir_name)
					shutil.copytree(sounds_dir, store_sounds_dir)

	def export_all(self,
			out_path: str | os.PathLike,
			animation_format: str = "mp4",
			scale_factor: int = 1,
			thumb_scale_factor: int = 1,
			include_sound: bool = True,
			video_codec: str | None = None,
			audio_codec: str | None = None,
			ffmpeg_params: Iterable[str] = None) -> None:
		"""
		Exports everything in the Flipnote to an output path and creats an animation with the given format.

		This si a quick way to dump entire PPM files with a single function. If you only want an aniamtion, use `export_video()` or `export_gif()`. If you just want frames or sounds, use `export_frames()` or `export_sounds()` respectively. If all you want is the Flipnote thumbnail or the metadata, use `export_thumbnail()` or `export_metadata()`.

		Parameters
		----------
		self : PPM
			PPM instance
		out_path : str | os.PathLike
			Output path for the complete export
		animation_format : str (defult = "mp4")
			The format to export the animation. Supports all FFPmeg-compatible formats
		scale_factor : int (default = 1)
			Factor to upscale each frame of the animation
			- 1 = Native `256px x 192px`
			- 2 = 2x upscale `512px x 384px`
			- 4 = 4x upscale `1024px x 768px`
			- ...
		scale_factor : int (default = 1)
			Factor to upscale the thumbnail of the Flipnote by
			- 1 = Native `64px x 48px`
			- 2 = 2x upscale `128px x 96px`
			- 4 = 4x upscale `256px x 192px`
			- ...
		include_sound : bool (default = True)
			Whether to export the video with sound or not. Is forced to `False` if the Flipnote has no sound data
		video_codec : str | None (default = None)
			Video codec to be passed to MoviePy on export. If `None`, default settings will be used
		audio_codec : str | None (default = None)
			Audio codec to be passed to MoviePy on export. If `None`, default settings will be used. Ignored if `include_sound = False`
		ffmpeg_params : Iterable[str] (defualt = None)
			Additional FFMpeg parameters to pass to MoviePy on export. Ignored if `None`
		"""

		if not HAS_MOVIEPY:
			raise PPMMissingDependency("moviepy")
		
		# Force no sound if we don't even have any
		if not any(self.raw_sound_data):
			include_sound = False

		# Set up kwargs for MoviePy
		codec_kwargs = {}
		if not include_sound:
			codec_kwargs["audio"] = None
		if video_codec is not None:
			codec_kwargs["codec"] = video_codec
		if audio_codec is not None and include_sound:
			codec_kwargs["audio_codec"] = audio_codec
		if ffmpeg_params is not None:
			codec_kwargs["ffmpeg_params"] = ffmpeg_params
		
		# Make path absolute and break base to check if its a file
		export_dir = os.path.join(os.path.abspath(out_path), self.input_filename)
		final_file = os.path.join(export_dir, f"{self.input_filename}.{animation_format}")

		# Make directories
		os.makedirs(export_dir, exist_ok=True)

		# Export metadata
		self.export_metadata(export_dir)

		# Export thumbnail
		self.export_thumbnail(export_dir, scale_factor=thumb_scale_factor)

		# Open temporary directories for frames and sounds
		with TemporaryDirectory(prefix="ppm_frames_") as frames_dir:
			with TemporaryDirectory(prefix="ppm_sounds_") as sounds_dir:
				# Export frames
				self.export_frames(frames_dir, scale_factor=scale_factor)

				# Create ImageSequenceClip
				video = self.exported_frames_to_image_sequence_clip(frames_dir)

				# If we want sounds
				if include_sound:
					# Export sounds
					self.export_sounds(sounds_dir, export_original_bgm_speed=True)

					# Compose sounds and merge with video
					composite_sounds = self.compose_audio(sounds_dir)
					video = video.set_audio(composite_sounds)
				
				# Ensure video duration is set properly
				video.set_duration(self.duration)

				# Check animation type
				match animation_format.lower():
					case "gif":
						video.write_gif(final_file, program="ffmpeg")
					case _:
						video.write_videofile(final_file, **codec_kwargs)

				# Clean up leftover data to free up memory
				self._clean_up_garbage()
				gc.collect()

				# Move frames
				print("Copying frames...")
				store_frames_dir = os.path.join(export_dir, self.frames_outdir_name)
				shutil.copytree(frames_dir, store_frames_dir)

				# Move sounds
				print("Copying sounds...")
				store_sounds_dir = os.path.join(export_dir, self.sounds_outdir_name)
				shutil.copytree(sounds_dir, store_sounds_dir)