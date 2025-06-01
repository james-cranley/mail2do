"""
Setup script for the mail2do package.
"""

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mail2do",
    version="0.1.0",
    description="Automated pipeline converting emails into Notion to-do items",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="James Cranley",
    author_email="james.cranley@doctors.org.uk",
    url="https://github.com/jamescranley/mail2do",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "python-dotenv",
        "requests",
        "openai>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mail2do=mail2do.cli:main",
            "mail2do-configure=mail2do.configure:main",
            "mail2do-fetch-emails=mail2do.fetch_emails:fetch_emails",
            "mail2do-get-schema=mail2do.notion_get_schema:main",
            "mail2do-parse-emails=mail2do.parse_emails:main",
            "mail2do-upload=mail2do.notion_upload:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)