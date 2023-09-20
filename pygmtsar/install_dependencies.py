import sys
import subprocess

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = [
    'contourpy>=1.0.1',
    'cycler>=0.10',
    'fonttools>=4.22.0',
    'kiwisolver>=1.0.1',
    'pillow>=6.2.0',
    'pyparsing>=2.3.1',
    'certifi',
    'llvmlite<0.42,>=0.41.0dev0',
    'six',
    'imageio',
    'slicerator>=0.9.8',
    'affine',
    'attrs',
    'click-plugins',
    'cligj>=0.5',
    'snuggs>=1.4.1'
]

for package in packages:
    install(package)
