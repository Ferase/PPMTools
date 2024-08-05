import os
import sys
import glob
import shutil
import argparse
import PPMTools as ppm

# Define an exception catcher that will keep the terminal open during an exception
def show_exception_and_exit(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Press return to exit.")
    sys.exit(-1)

sys.excepthook = show_exception_and_exit # Set exception hook



CWD = os.path.abspath(os.path.dirname(__file__))
IMG_FOLER_NAME = "img"
SND_FOLDER_NAME = "snd"

parser = argparse.ArgumentParser(
    prog="PPMTools Studio",
    description="A parser and exporter for Flipnote Studio PPM files. Original code from Hatenatools by pbsds (Peder Bergebakken Sundt) and restructured and optimized for Python 3 by Ferase (Parker Lippstock)"
)
parser.add_argument(
    dest="files",
    nargs="*",
    type=str,
    help="Flipnote Studio PPM file(s) to process. Invoked when dragging PPM files onto this script, ignores -i"
)
parser.add_argument(
    "-i", "--indir",
    dest="in_dir",
    type=os.path.abspath,
    help="Input directory containing PPM files. WIll be ignored if single files are provided via the files argument"
)
parser.add_argument(
    "-o", "--outdir",
    dest="out_dir",
    type=os.path.abspath,
    default=os.path.join(CWD, "output"),
    help="Output directory for dumped/exported data"
)
parser.add_argument(
    "-u", "--upscale",
    dest="scale_factor",
    type=int,
    default=1,
    help="Upscale frames by a scale factor. Default is native resolution (scale_factor = 1), which is 256px x 192px"
)
parser.add_argument(
    "-a", "--all",
    dest="dump_all",
    action="store_true",
    help="Dumps everything possible, doesn't delete any leftover data after MP4/GIF export"
)
parser.add_argument(
    "-k", "--keepall",
    dest="keep_all",
    action="store_true",
    help="Keep all data after dumping and exporting, don't delete anything"
)
parser.add_argument(
    "-f", "--keepframes",
    dest="keep_frames",
    action="store_true",
    help="Doesn't delete frames after export. If set, all extracted resources will be put into a child folder inside of the output directory"
)
parser.add_argument(
    "-sf", "--skipframes",
    dest="skip_frames",
    action="store_true",
    help="Skips exporting frames altogether. Also skips exporting MP4/GIF"
)
parser.add_argument(
    "-s", "--keepsounds",
    dest="keep_sounds",
    action="store_true",
    help="Doesn't delete sounds after export. If set, all extracted resources will be put into a child folder inside of the output directory"
)
parser.add_argument(
    "-ss", "--skipsounds",
    dest="skip_sounds",
    action="store_true",
    help="Skips exporting sounds altogether"
)
parser.add_argument(
    "-t", "--dumpthumb", "--dumpthumbnail",
    dest="dump_thumb",
    action="store_true",
    help="Dump the Flipnote's thumbnail image"
)
parser.add_argument(
    "-m", "--dumpmeta", "--dumpmetadata",
    dest="dump_meta",
    action="store_true",
    help="Dump the Flipnote's metadata into a JSON file"
)
parser.add_argument(
    "-x", "--skipexport",
    dest="skip_export",
    action="store_true",
    help="Skip exporting Flipnote as an MP4 or GIF. Pair this with -k, -f, -s, -t, and/or -m to just get the data"
)
parser.add_argument(
    "-e", "--exporttype",
    dest="export_type",
    choices=["MP4", "GIF"],
    type=str,
    default="MP4",
    help="Whether to export video as MP4 or GIF"
)
parser.add_argument(
    "-c", "--copyppm",
    dest="copy_ppm",
    action="store_true",
    help="Copy Flipnote PPM file to output directory"
)

args = parser.parse_args()



def GetInFiles():

    # Priprotize single files
    if args.files:
        return args.files
    elif args.in_dir:
        return glob.glob(os.path.join(os.path.abspath(args.in_dir), "*.ppm"))

# Create output folders
def CreateDumpDir(flip_name: str):

    # Set dump dir
    dump_dir = os.path.join(args.out_dir, flip_name)

    # If the directory exists, delete it so we can start fresh
    if os.path.exists(dump_dir):
        shutil.rmtree(dump_dir)
    
    # Make output directory tree
    os.makedirs(dump_dir)

    return dump_dir


# Get files from args
FILES = GetInFiles()

# Close script if no files were provided
if not FILES:
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
    dump_dir = CreateDumpDir(flip_name)

    # Output files to output dir if user isn't keeping all, frames, and/or sounds
    output_dir = args.out_dir

    # Check all arguments for keeping dumped items. We only care about frames and sounds here since the thumbnail and metadata will be named the same as the Flipnote
    keeping_dumps = any([args.dump_all, args.keep_all, args.keep_frames, args.keep_sounds])

    # Set the output dir to the dumping dir if they are keeping all, frames, and/or sounds
    if keeping_dumps:
        output_dir = dump_dir

    # Get animation stream settings
    speed, fps, duration = flip.GetAnimationStreamSettings()

    # Export metadata if requested
    if args.dump_all or args.dump_meta:
        flip.ExportMetadata(output_dir, flip_name)

    # Export thumbnail image if requested
    if args.dump_all or args.dump_thumb:
        flip.ExportThumbnail(output_dir, flip_name)

    if not args.skip_frames:
        # Set and create images dir
        images_dir = os.path.join(dump_dir, IMG_FOLER_NAME)
        os.mkdir(images_dir)

        # Dump images to the flip_name/img folder and set scale if user defined a different factor
        flip.DumpFrames(images_dir, args.scale_factor)

        # Create a moviepy image sequence
        image_sequence = flip.CreateImageSequence(images_dir, fps)

    # Set audio composite to None if there is no sound
    audio_composite = None

    # If we aren't skipping sounds, extract and composite them
    if not args.skip_sounds:
        # Set and create sounds dir
        sounds_dir = os.path.join(dump_dir, SND_FOLDER_NAME)
        os.mkdir(sounds_dir)

        # Check if the Flipnote has sound
        has_sound = flip.CheckIfSoundDataExists()
        if has_sound:
            # Dump sound files to the flip_name/snd folder
            flip.DumpSoundFiles(sounds_dir)

            # Create audio composite using dumped audio
            audio_composite = flip.CompositeAudio(sounds_dir, fps)

    # Check if we can export an MP4/GIF
    allow_export = not any([args.skip_export, args.skip_frames])

    # If we can export MP4/GIF
    if allow_export:
        # Export requested animation type
        match args.export_type:
            case "MP4":
                flip.ExportVideo(flip_name, output_dir, fps, image_sequence, audio_composite)
            case _:
                flip.ExportGIF(flip_name, output_dir, fps, image_sequence)

    # If we're keeping anything we dump (but not always everything)
    if keeping_dumps:

        # Check what we are deleting
        delete_frames = any([args.skip_frames, args.keep_frames])
        delete_sounds = any([args.skip_sounds, args.keep_sounds])

        # If we're not keeping frames, delete them
        if delete_frames:
            shutil.rmtree(images_dir)

        # If we're not keeping sounds, delete them
        if delete_sounds:
            shutil.rmtree(sounds_dir)

    # Delete dump directory otherwise
    else:
        shutil.rmtree(dump_dir)

        

    # Copy PPM file to output directory
    if args.dump_all or args.copy_ppm:
        shutil.copy2(flipnote_path_absolute, output_dir)