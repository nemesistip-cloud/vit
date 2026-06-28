import setuptools

setuptools.setup(
    name="vit-node",
    version="0.1.0",
    packages=setuptools.find_packages(),
    install_requires=[
        "click",
        "httpx",
        "websockets",
        "cryptography",
        "google-auth-oauthlib",
        "google-api-python-client",
        "tabulate",
        "coincurve",
        "eth-hash[pycryptodome]"
    ],
    entry_points={
        "console_scripts": [
            "vit-node=vit_node.cli:cli",
        ],
    },
)
