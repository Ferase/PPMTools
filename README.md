# PPMTools

A fork of [Hatenatools](https://github.com/pbsds/Hatenatools) by [pbsds aka Peder Bergebakken Sundt](https://pbsds.net/)

**PPMTools** is a Python module that takes the PPM parsing script from Hatenatools, which was written for Python 2, and restructures it for use with Python 3.

## Requirements

PIL (pillow), moviepy, and numpy are required to use this module.

## Example

An exmaple script is included that shows how to use the module. Drag one or multiple PPM files onto the `example.py` script and it will export a folder with the following structure:

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
        metadata.json
        thumbnail.png
```

## Credits

All original code by [pbsds aka Peder Bergebakken Sundt](https://pbsds.net/) and other contributors to teh original Hatenatools project. The original Hatenatools README has been included as [Hatenatools_readme.txt](https://github.com/Ferase/PPMTools/blob/master/Hatenatools_readme.txt).

If the authors of Hatenatools wish this repository to be taken down, please contact me and it will be done.

## License

Current and original repository are licensed under AGPL v3.
