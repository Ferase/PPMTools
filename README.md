# PPMTools

A fork of [Hatenatools](https://github.com/pbsds/Hatenatools) by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/)

**PPMTools** is a Python module that takes the PPM parsing script from Hatenatools, which was written for Python 2, and restructures it for use with Python 3.

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

3. Import the parsing script from the module:
```python
import PPMTools.ppm_parse
```

## Example

[example.py](https://github.com/Ferase/PPMTools/blob/master/example.py) is an example usage of PPMTools that does the following:

1. Instantiates the PPM class and loads a Flipnote
2. Creates an output directory tree
3. Dumps the metadata, thumbnail, frames, and sounds (if there are any) to the output directory
4. Composites frames and audio into a moviepy video
5. Exports the video to the output directory as MP4
6. Copies the PPM file to the output directory (for categorization, since these things are tough to sift through if you have a lot)

The final directory tree will look like this:

```text
output
    input_file_name
        img
            000.png
            001.png
            002.png
            ...
        snd
            BGM.wav
            BGM_SPEED.wav
            SFX1.wav
            SFX2.wav
            SFX3.wav
        input_file_name.mp4
        input_file_name.ppm
        metadata.json
        thumbnail.png
```

## Credits

All original code by [pbsds (Peder Bergebakken Sundt)](https://pbsds.net/) and other contributors to teh original Hatenatools project. The original Hatenatools README has been included as [Hatenatools_readme.txt](https://github.com/Ferase/PPMTools/blob/master/Hatenatools_readme.txt).

If the authors of Hatenatools wish this repository to be taken down, please contact me and it will be done.

## License

Current and original repository are licensed under AGPL v3.
