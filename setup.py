from setuptools import setup, find_packages

from stockrt import __version__
srt_name = 'stockrt'

setup(
    name=srt_name,
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=["requests"]
)
