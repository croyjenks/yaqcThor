from distutils.core import setup

setup(name='yaqcThor', 
    version='0.1.0',
    description="Experiment orchestration methods for the Wright Group PL microscope.",
    author="Chris Roy, Song Jin and John C. Wright Research Groups, Department of Chemistry, University of Wisconsin-Madison",
    packages=['yaqcThor'],
    py_modules=['experiments','helpers','constants']
    )