from setuptools import setup, find_packages
import re

srt_name = 'stockrt'
version = ''
with open('stockrt/__init__.py', 'r') as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        f.read(),
        re.MULTILINE).group(1)

setup(
    name=srt_name,
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=["requests"]
)
