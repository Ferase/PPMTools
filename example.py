import os
import sys
import shutil
import ppmtools.ppm_parse as ppm

CWD = os.path.abspath(os.path.dirname(__file__))
OUT_DIR = os.path.join(CWD, "output")
IMG_FOLER_NAME = "img"
SND_FOLDER_NAME = "snd"
THUMNAIL_NAME = "thumnail"
METADATA_FILE_NAME = "metadata"



# Create output folders
def CreateOutputDir(flip_name: str):
    global OUT_DIR, IMG_FOLER_NAME, SND_FOLDER_NAME

    output_dir = os.path.join(OUT_DIR, flip_name)
    images_dir = os.path.join(OUT_DIR, flip_name, IMG_FOLER_NAME)
    soudns_dir = os.path.join(OUT_DIR, flip_name, SND_FOLDER_NAME)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    os.makedirs(os.path.join(output_dir, IMG_FOLER_NAME))
    os.mkdir(os.path.join(output_dir, SND_FOLDER_NAME))

    return output_dir, images_dir, soudns_dir

# Get all files overloaded into script, close script if no files were provided
try:
    FILES = sys.argv[1:]
except IndexError:
    input("No files were given!")
    exit()

# Loop through all files
for flipnote in FILES:

    # Get absolute path to flipnote
    flipnote_path_absolute = os.path.abspath(flipnote)

    # Instantiate PPM class and read flipnote
    PPM_INSTANCE = ppm.PPM()
    flip = PPM_INSTANCE.ReadFile(flipnote_path_absolute)

    # Get the name of the input PPM file without extension
    flip_name = os.path.splitext(os.path.basename(flipnote))[0]

    # Create paths and return them in full, relative to CWD
    output_dir, images_dir, sounds_dir = CreateOutputDir(flip_name)

    # Get animation stream settings
    speed, fps, duration = flip.GetAnimationStreamSettings()

    # Export metadata
    flip.ExportMetadata(output_dir, METADATA_FILE_NAME)

    # Export thumbnail image
    flip.ExportThumbnail(output_dir, THUMNAIL_NAME)

    # Dump images to the flip_name/img folder
    flip.DumpFrames(images_dir)

    # Create a moviepy image sequence
    image_sequence = flip.CreateImageSequence(images_dir, fps)

    # Check if the Flipnote has sound
    has_sound = flip.CheckIfSoundDataExists()

    # Set audio composite to None if there is no sound
    audio_composite = None
    if has_sound:

        # Dump sound files to the flip_name/snd folder
        flip.DumpSoundFiles(sounds_dir)

        # Create audio composite using dumped audio
        audio_composite = flip.CompositeAudio(sounds_dir, fps)
    
    # Export video as MP4
    flip.ExportVideo(output_dir, fps, image_sequence, audio_composite, True)