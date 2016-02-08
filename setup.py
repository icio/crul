#!/usr/bin/env python
from setuptools import setup

VERSION = "1.0"

setup(
    name="crul",
    version=VERSION,
    description="Website Crawler",
    author="Paul Scott",
    author_email="paul.scotto@gmail.com",
    url="https://github.com/icio/crul",
    download_url="https://github.com/icio/crul/tarball/%s" % VERSION,
    packages=["crul"],
    entry_points={
        'console_scripts': ['crul=crul.__main__:main'],
    },
    install_requires=[
        'beautifulsoup4==4.4.1',
        'docopt==0.6.2',
        'requests==2.9.1',
        'sloq==0.2',
        'lxml==3.5.0',
    ],
    tests_require=[
        'setuptools==20.0',
        'responses==0.5.1',
    ],
    test_suite="crul.test",
    license="MIT",
    keywords=['crawl', 'scrape'],
    classifiers=[],
)
