import time
from binascii import hexlify

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

# Functions --------------------

# ASCII string to decimal
def AscDec(ascii, LittleEndian = False):
	ret = 0
	l = []

	for num in ascii:
		l.append(num)

	if LittleEndian: l.reverse()
	for i in l:
		ret = (ret<<8) | i
		
	return ret

# Decimal to ASCII string of specified length
def DecAsc(dec, length = None, LittleEndian = False):
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
def AddPadding(i, pad = 0x10):
	if i % pad != 0:
		return i + pad - (i % pad)
	return i

# Decimal to hexadecimal
def ToHex(num) -> bytes:
	return hexlify(num).upper()

# Decode string from data slice and remove trailing break
def DecodeString(data_slice: bytes):
	return data_slice.decode("UTF-16LE").split("\0")[0]

def DecompressFilename(compressed_filename: bytes) -> tuple[bytes, bytes, str]:
	first = ToHex(compressed_filename[:3])
	second = compressed_filename[3:-2]
	third = str(AscDec(compressed_filename[-2:], True)).zfill(3)

	return first, second, third

# Seconds since Jan 1st, 1970 converted to date
def FormattedDateFromEpoch(datecode: bytes):
	epoch = time.mktime(time.struct_time([2000, 1, 1, 0, 0, 0, 5, 1, -1]))

	seconds = AscDec(datecode, True)
	unformatted_date = time.gmtime(epoch+seconds)

	return time.strftime(
		"%A, %B %d, %Y, %I:%M:%S %p", # Dayname, monthname day, year, 12hour:minute:second meridiem
		unformatted_date
	)

# Get the size of a sound block
def GetSoundSize(audio_offset, frame_count, offset, lower_bound=False) -> bytes:

	if lower_bound:
		return AddPadding(audio_offset+frame_count, 4) + (4+offset)

	return AddPadding(audio_offset+frame_count, 4) + offset

# Converts internally stored filenames to proper strings
def FilenameToString(file_name: tuple):
	return "_".join([str(file_name[0])[2:-1], str(file_name[0])[2:-1], str(file_name[2])[2:-1]]) + ".pmm"