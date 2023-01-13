__name__ = "constants"
__author__ = "Chris R. Roy, Song Jin and John C. Wright Research Groups, Dept. of Chemistry, University of Wisconsin-Madison"
__version__ = '0.1.0'

"""
Constant parameters of the PL microscope.
"""

APD_PIXEL = (1325, 1080)

GRATING_WINDOWS_NM = {
    '150' : 360,
    '1200' : 45
}

OBJECTIVE_CALIBRATION_SCALES = { #scales in pixels/um
    '5' : 0.893,
    '20' : 3.52,
    '100' : 18.2
}