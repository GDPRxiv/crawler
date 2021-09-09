import setuptools

#with open("README.md", "r") as fh:
#    long_description = fh.read()

setuptools.setup(
    name="pygdpr-daniel-lehmann",
    version="0.0.1",
    author="Daniel Lehmann",
    author_email="zfx206@alumni.ku.dk",
    description="A GDPR webscraper designed to get, translate, extract metadata and classify kinds of documents relating to the regulation.",
    long_description="A GDPR webscraper designed to get, translate, extract metadata and classify kinds of documents relating to the regulation.",
    long_description_content_type="text/markdown",
    url="https://github.com/DanielRanLehmann/pygdpr",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
