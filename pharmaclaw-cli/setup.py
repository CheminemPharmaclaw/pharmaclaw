from setuptools import setup, find_packages

setup(
    name="pharmaclaw-cli",
    version="1.0.0",
    description="PharmaClaw CLI — Unified drug discovery agent team at your fingertips",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="PharmaClaw Team",
    author_email="cheminem602@gmail.com",
    url="https://pharmaclaw.com",
    py_modules=["pharmaclaw_cli"],
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "rdkit",
        "pubchempy",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "pharmaclaw=pharmaclaw_cli:pharmaclaw",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
)
