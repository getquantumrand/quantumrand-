from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="quantumrand-sdk",
    version="1.0.0",
    description="True quantum randomness from Origin Wukong — one line of code.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="QuantumRand",
    author_email="jbearswrld@proton.me",
    url="https://quantumrand.dev",
    packages=find_packages(),
    install_requires=["requests>=2.28.0"],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Topic :: Security :: Cryptography",
        "Operating System :: OS Independent",
    ],
)
