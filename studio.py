import os
import sys
import glob
import shutil
import argparse
from PPMTools import PPM

# Define an exception catcher that will keep the terminal open during an exception
def show_exception_and_exit(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    input("Press return to exit.")
    sys.exit(-1)

sys.excepthook = show_exception_and_exit # Set exception hook

CWD = os.path.abspath(os.path.dirname(__file__))



# Set up arguments
parser = argparse.ArgumentParser(
    prog="PPMTools Studio",
    description="A parser and exporter for Flipnote Studio PPM files. Original code from Hatenatools by pbsds (Peder Bergebakken Sundt) and restructured and optimized for Python 3 by Ferase (Parker Lippstock)"
)
parser.add_argument(
    dest="files",
    nargs="*",
    type=str,
    help="Flipnote PPM files to process. Can be a list of files, folders, or both"
)
parser.add_argument(
    "-o", "--outdir",
    dest="out_dir",
    default=None,
    help="Output directory for dumped/exported data"
)
parser.add_argument(
    "-e", "--format",
    dest="format",
    choices=["mp4", "webm", "avi", "gif"],
    type=str,
    default="mp4",
    help="Animation format to export the Flipnote to. Defualt is MP4"
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
    "-f", "--keepframes",
    dest="keep_frames",
    action="store_true",
    help="Doesn't delete frames after export. If set, all extracted resources will be put into a child folder inside of the output directory"
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
    "-tu", "--thumbupscale",
    dest="thumb_scale_factor",
    type=int,
    default=1,
    help="Upscale thumbnail image a scale factor. Default is native resolution (scale_factor = 1), which is 64px x 48px"
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
    "-c", "--copyppm",
    dest="copy_ppm",
    action="store_true",
    help="Copy Flipnote PPM file to output directory"
)

args = parser.parse_args()



# Create list of PPM files based on passed list
if args.files:
    new_files = []

    # GO through the files argument
    for item in args.files:
        # Set up paths
        absolute_item_path = os.path.abspath(os.path.dirname(item))
        file_name, file_extension = os.path.splitext(os.path.basename(item))

        # If the file extension is present, we're likely being pointed towards a file
        if file_extension:
            new_files.append(item)
        # If not, it's probably a dir, so look for PPMs inside of it
        else:
            for ppm_file in glob.glob(os.path.join(item, "*.ppm")):
                new_files.append(ppm_file)
else:
    input("No PPM files were passed, exiting")
    exit()

# Iterate through all files
for file in new_files:

    # Swap boolean for sounds check
    has_sound = not args.skip_sounds

    # Set output directory based on if the user is keeping frames or sounds
    if not args.out_dir:
        if any([args.keep_frames, args.keep_sounds]) and not args.dump_all:
            final_out_dir = os.path.join(CWD, "output", os.path.splitext(os.path.basename(file))[0])
        # export_all() handles exporting to subdirectories
        else:
            final_out_dir = os.path.join(CWD, "output")
    
    # Instantiate PPM class with PPM file
    flip = PPM(file)

    # If we want it all, we get it all
    if args.dump_all:
        flip.export_all(final_out_dir, args.format, args.scale_factor, args.thumb_scale_factor, has_sound)
    
    else:
        # Dump metadata if we want it
        if args.dump_meta:
            flip.export_metadata(final_out_dir)

        # Dump thumbnail if we want it
        if args.dump_thumb:
            flip.export_thumbnail(final_out_dir, scale_factor=args.thumb_scale_factor)

        # If we aren't exporting an animation, we cab stukk exoirt frames and sounds if we want to
        if args.skip_export:
            if args.keep_frames:
                flip.export_frames(final_out_dir, scale_factor=args.scale_factor)
            if args.keep_sounds and not args.skip_sounds:
                flip.export_sounds(final_out_dir, scale_factor=args.scale_factor)

        else:
            # Check format for animation export
            match args.format.lower():
                # Use GIF function if we are exporting a GIF
                case "gif": 
                    flip.export_gif(os.path.join(final_out_dir, os.path.splitext(os.path.basename(file))[0] + f".gif"), scale_factor=args.scale_factor, keep_temp_frames=args.keep_frames, export_audio=args.keep_sounds)

                # Everything else will be a video
                case _:
                    include_audio = not args.skip_sounds

                    flip.export_video(os.path.join(final_out_dir, os.path.splitext(os.path.basename(file))[0] + f".{args.format}"), scale_factor=args.scale_factor, include_sound=include_audio, keep_temp_frames=args.keep_frames, keep_temp_sounds=args.keep_sounds)

    # Copy out the PPM file if we want it
    if args.copy_ppm:
        shutil.copy2(file, os.path.join(final_out_dir, os.path.splitext(os.path.basename(file))[0]))