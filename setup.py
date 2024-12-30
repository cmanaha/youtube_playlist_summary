from setuptools import setup, find_packages

setup(
    name="youtube-playlist-analyzer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv>=1.0.0",
        "langchain>=0.1.0",
        "langchain-community>=0.0.13",
        "youtube-transcript-api>=0.6.1",
        "yt-dlp>=2024.3.10",
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.3',
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.12.0',
            'responses>=0.24.1',
        ]
    }
) 