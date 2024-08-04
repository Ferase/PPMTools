# Raise if the provided flipnote isn't valid
class PPMBinaryNotValid(Exception):
    """
    Raised if the binary data can't be interpreted as PPM data.
    """

    def __init__(self, message="Cannot interpret provided data as PPM data."):
        self.message = message
        super().__init__(self.message + " Your Flipnote may be corrupted.")

# Raise if the user tries to access data that wasn't loaded or doesn't exist
class PPMDataNotLoaded(Exception):
    """
    Raised if an attempt is made to access data that hasn't been loaded.
    """

    def __init__(self, data="UNKNOWN"):
        self.message = f"{data} data was requested but wasn't loaded. Please check your ReadFile() and ReadBytes() calls and be sure you are allowing this data do be read."
        super().__init__(self.message)

# Raise if the user hasn't installed PIL
class PPMNoPIL(Exception):
    """
    Raised if the user doesn't have PIL and uses a function that needs it.
    """

    def __init__(self, message="You do not have PIL installed. Please install PIL to export frames from a PPM file (pip install pillow)"):
        self.message = message
        super().__init__(self.message)

# Raise if the user hasn't installed moviepy
class PPMNoMoviepy(Exception):
    """
    Raised if the user doesn't have moviepy and uses a function that needs it.
    """

    def __init__(self, message="You do not have moviepy installed. Please install moviepy to export frames from a PPM file (pip install moviepy)"):
        self.message = message
        super().__init__(self.message)

# Raise if the provided flipnote isn't valid
class PPMNoFFMPEG(Exception):
    """
    Raised if the user doesn't have FFMPEG and uses a function that needs it.
    """

    def __init__(self, message="FFMPEG not found. Either it isn't installed or its location isn't mapped to your PATH variable in your system or environment. Please download FFMPEG and add it to your systtem or environment PATH (https://www.ffmpeg.org/download.html)"):
        self.message = message
        super().__init__(self.message)

# Raise if the provided flipnote isn't valid
class PPMNoAudio(Exception):
    """
    Raised if the user tries to dump audio from a PPM that has no audio.
    """

    def __init__(self, message="This PPM either has no audio, or you loaded it with ReadSound = False in ReadFile() or ReadBytes()."):
        self.message = message
        super().__init__(self.message)