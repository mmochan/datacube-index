import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="datacube-index",
    version="0.0.1",
    author="Geoscience Australia",
    author_email="earth.observation@ga.gov.au",
    description="An application to index data from S3 to Datacube PosgreSQL Database",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/opendatacube/datacube-index",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=["Click",],
    entry_points="""
        [console_scripts]
        s3-to-dc=odc_index.s3_to_dc:cli
        thredds-to-dc=odc_index.thredds_to_dc:cli
        sqs-to-dc=odc_index.sqs_to_dc:cli
        stac-to-dc=odc_index.stac_appi_to_dc:cli
    """,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
