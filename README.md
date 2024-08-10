# PPMTools

A fork of [Hatenatools](https://github.com/pbsds/Hatenatools) by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/)

**PPMTools** is a Python script to be used as an importable module. It can read any PPM format Flipnote and dmup its frames, sounds, thumbnail, and metadata, as well as reconstruct the Flipnote into a video or GIF.

## Usage

Currently, PPMTools is not set up as a Python package. For now, you can utilize this module by doing the following:

1. Clone this repository with by clicking the green `Code` button and choosing `Downlaod ZIP` button, then unzip it after it downloads. Alternatively, you can use use Git with the following command:

```text
git clone https://github.com/Ferase/PPMTools
```

2. Install requirements:

```text
pip install -r requirements.txt
```

3. Put the module in the same folder as your script and import the PPM class:

```python
from PPMTools import PPM
```

## Example

[studio.py](https://github.com/Ferase/PPMTools/blob/master/studio.py) is an example script to illustrate usage of PPMTools. It is a customizable exporter that runs off of the command line and takes various arguments.

Here is the script's help command:

```text
usage: PPMTools Studio [-h] [-o OUT_DIR] [-e {mp4,webm,avi,gif}] [-u SCALE_FACTOR] [-a] [-f] [-s] [-ss] [-t]
                       [-tu THUMB_SCALE_FACTOR] [-m] [-x] [-c]
                       [files ...]

A parser and exporter for Flipnote Studio PPM files. Original code from Hatenatools by pbsds (Peder Bergebakken Sundt)
and restructured and optimized for Python 3 by Ferase (Parker Lippstock)

positional arguments:
  files                 Flipnote PPM files to process. Can be a list of files, folders, or both

options:
  -h, --help            show this help message and exit
  -o OUT_DIR, --outdir OUT_DIR
                        Output directory for dumped/exported data
  -e {mp4,webm,avi,gif}, --format {mp4,webm,avi,gif}
                        Animation format to export the Flipnote to. Defualt is MP4
  -u SCALE_FACTOR, --upscale SCALE_FACTOR
                        Upscale frames by a scale factor. Default is native resolution (scale_factor = 1), which is
                        256px x 192px
  -a, --all             Dumps everything possible, ignores -f, -s, -ss, -t, -m, and -x
  -f, --keepframes      Doesn't delete frames after export. If set, all extracted resources will be put into a child
                        folder inside of the output directory
  -s, --keepsounds      Doesn't delete sounds after export. If set, all extracted resources will be put into a child
                        folder inside of the output directory
  -ss, --skipsounds     Skips exporting sounds altogether
  -t, --dumpthumb, --dumpthumbnail
                        Dump the Flipnote's thumbnail image
  -tu THUMB_SCALE_FACTOR, --thumbupscale THUMB_SCALE_FACTOR
                        Upscale thumbnail image a scale factor. Default is native resolution (scale_factor = 1), which
                        is 64px x 48px
  -m, --dumpmeta, --dumpmetadata
                        Dump the Flipnote's metadata into a JSON file
  -x, --skipexport      Skip exporting Flipnote as an MP4 or GIF. Pair this with -k, -f, -s, -t, and/or -m to just get
                        the data
  -c, --copyppm         Copy Flipnote PPM file to output directory
```

As a module, PPMTools can be instantiated with a PPM file, adn then various functions can be used on the PPM object.

```python
# Import PPM
from PPMTools import PPM

# Instantiate PPM
flip = PPM("myflip.ppm")

# Data functions
flip.raw_thumbnail_to_array(...) # Converts raw thumbnail bytes to NumPy array
flip.raw_frame_to_array(...) # Converts raw frame bytes to NumPy array
flip.sound_data_to_4bit_adpcm(...) # Converts raw sound bytes to 4bit ADPCM audio data

# Export functions
flip.export_metadata(...) # Exports Flipnote metadata as a JSON file
flip.export_thumbnail(...) # Exports Flipnote thumbnail image
flip.export_frames(...) # Exports Flipnote frames
flip.export_sounds(...) # Exports Flipnote sounds
flip.export_video(...) # Exports the entire Flipnote as a video
flip.export_gif(...) # Exports the entire Flipnote as a GIF
flip.export_all(...) # Exports all data in the Flipnote at once and export a video/GIF

# Other functions
flip.exported_frames_to_image_sequence_clip(...) # Merges exported frames into a MoviePy ImageSequenceClip
flip.sfx_usage_to_dict(...) # Creates a dictionary referencing on which frame index each of the SFX should play
flip.compose_audio(...) # Merges exported audio into a MoviePy CompositeAudioClip, properly placing SFX
```

## Credits

All original code by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/) and other contributors to the original Hatenatools project. The original Hatenatools README has been included as [Hatenatools_readme.txt](https://github.com/Ferase/PPMTools/blob/master/Hatenatools_readme.txt).

If the authors of Hatenatools wish this repository to be taken down, please contact me and it will be done.

## License

Current and original repository are licensed under AGPL v3.
