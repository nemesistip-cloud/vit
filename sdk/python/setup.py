from setuptools import setup, find_packages

setup(
    name="vit-sdk",
    version="0.1.0",
    description="Python SDK for the VIT Network (Value Analytics Trust)",
    long_description=open("../../sdk/README.md").read() if hasattr(open("../../sdk/README.md"), "read") else "",
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
