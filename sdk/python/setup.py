import os
from setuptools import setup, find_packages

# Robust README resolution
base_dir = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(base_dir, "..", "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="vit-sdk",
    version="0.1.0",
    description="Python SDK for the VIT Network (Value Analytics Trust)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="VIT Network Developers",
    url="https://github.com/Value-analytics-trust/vit-sdk",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.23.0",
        "coincurve>=17.0.0",
        "pydantic>=1.10.0",
        "eth-hash[pycryptodome]>=0.5.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
