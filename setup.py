from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sphinx-cmd",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Command-line tools for Sphinx documentation management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/sphinx-cmd",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "sphinx-cmd=sphinx_cmd.cli:main",
        ],
    },
)