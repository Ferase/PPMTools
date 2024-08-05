# PPMTools

A fork of [Hatenatools](https://github.com/pbsds/Hatenatools) by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/)

**PPMTools** is a Python script to be used as an importable module. It can read any PPM format Flipnote and dmup its frames, sounds, thumbnail, and metadata, as well as reconstruct the Flipnote into a video or GIF.

## Usage

Currently, PPMTools is not set up as a Python package. For now, you can utilize this module by doing the following:

1. Clone this repository with by clicking the green `Code` button and choosing `Downlaod ZIP` button, then unzip it after it downloads. Alternatively, you can use use Git with the following command:
```
git clone https://github.com/Ferase/PPMTools
```

2. Install requirements:
```
pip install -r requirements.txt
```

3. Put the module in the same folder as your script and import the parsing script from the module:
```python
import PPMTools
```

## Example

[studio.py](https://github.com/Ferase/PPMTools/blob/master/studio.py) is an example script to illustrate usage of PPMTools. It is a customizable exporter that runs off of the command line and takes various arguments.

Here is the script's `-h`, or help, command:

```text
usage: PPMTools Studio [-h] [-i IN_DIR] [-o OUT_DIR] [-a] [-k] [-f] [-sf] [-s] [-ss] [-t] [-m] [-x] [-e {MP4,GIF}]
                       [-c]
                       [files ...]

A parser and exporter for Flipnote Studio PPM files. Original code from Hatenatools by pbsds (Peder Bergebakken Sundt)
and restructured and optimized for Python 3 by Ferase (Parker Lippstock)

positional arguments:
  files                 Flipnote Studio PPM file(s) to process. Invoked when dragging PPM files onto this script,
                        ignores -i

options:
  -h, --help            show this help message and exit
  -i IN_DIR, --indir IN_DIR
                        Input directory containing PPM files. WIll be ignored if single files are provided via the
                        files argument
  -o OUT_DIR, --outdir OUT_DIR
                        Output directory for dumped/exported data
  -a, --all             Dumps everything possible, doesn't delete any leftover data after MP4/GIF export
  -k, --keepall         Keep all data after dumping and exporting, don't delete anything
  -f, --keepframes      Doesn't delete frames after export. If set, all extracted resources will be put into a child
                        folder inside of the output directory
  -sf, --skipframes     Skips exporting frames altogether. Also skips exporting MP4/GIF
  -s, --keepsounds      Doesn't delete sounds after export. If set, all extracted resources will be put into a child
                        folder inside of the output directory
  -ss, --skipsounds     Skips exporting sounds altogether
  -t, --dumpthumb, --dumpthumbnail
                        Dump the Flipnote's thumbnail image
  -m, --dumpmeta, --dumpmetadata
                        Dump the Flipnote's metadata into a JSON file
  -x, --skipexport      Skip exporting Flipnote as an MP4 or GIF. Pair this with -k, -f, -s, -t, and/or -m to just get
                        the data
  -e {MP4,GIF}, --exporttype {MP4,GIF}
                        Whether to export video as MP4 or GIF
  -c, --copyppm         Copy Flipnote PPM file to output directory
```

This example script will construct this file structure for a fully dumped PPM:

```text
output // Main output directory
    input_file_name // Child directory
        img // Frames folder
            000.png
            001.png
            002.png
            ...
        snd // Sounds folder
            BGM.wav
            BGM_<SAMPLE_RATE>HZ.wav
            SFX1.wav
            SFX2.wav
            SFX3.wav
        input_file_name.mp4 // Only if the user wanted MP4
        input_file_name.gif // Only if the user wanted GIF
        input_file_name.ppm // Original PPM
        input_file_name.json // Metadata
        input_file_name.png // Thumbnail
```

If the user wishes to only export an MP4/GIF, dump the thumbnail, dump the metadata, and/or copy the PPM file to store alongside the dump, then this is the folder structure that will be used instead:

```text
output // Main output directory
    input_file_name.mp4 // Only if the user wanted MP4
    input_file_name.gif // Only if the user wanted GIF
    input_file_name.ppm // Original PPM
    input_file_name.json // Metadata
    input_file_name.png // Thumbnail
```


## Credits

All original code by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/) and other contributors to the original Hatenatools project. The original Hatenatools README has been included as [Hatenatools_readme.txt](https://github.com/Ferase/PPMTools/blob/master/Hatenatools_readme.txt).

If the authors of Hatenatools wish this repository to be taken down, please contact me and it will be done.

## License

Current and original repository are licensed under AGPL v3.
