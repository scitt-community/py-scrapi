# setup.py
from setuptools import setup, find_packages

setup(
    name="py_scrapi",
    version="0.1.1",
    description="Python wrapper for IETF SCITT reference API (SCRAPI)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="JAG-UK",
    url="https://github.com/scitt-community/py-scrapi",
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "cbor2",
        "pycose",
        "rfc9290",
    ],
)
