"""
Test for SQS to DC tool
"""
import json
from functools import partial
from pprint import pformat

import pytest

from pathlib import Path

from datacube.utils import documents
from deepdiff import DeepDiff

from odc_index.sqs_to_dc import get_metadata_uri

# from odc.index.stac import stac_transform

TEST_DATA_FOLDER: Path = Path(__file__).parent.joinpath("data")
LANDSAT_C3_SQS_MESSAGE: str = "ga_ls8c_ard_3-1-0_088080_2020-05-25_final.stac-item.json"
LANDSAT_C3_ODC_YAML: str = "ga_ls8c_ard_3-1-0_088080_2020-05-25_final.odc-metadata.yaml"

deep_diff = partial(DeepDiff, significant_digits=6)


def test_sqs_to_dc(ga_ls8c_ard_3_message, ga_ls8c_ard_3_yaml):
    actual_doc, uri = get_metadata_uri(
        ga_ls8c_ard_3_message, None, "STAC-LINKS-REL:odc_yaml"
    )

    assert ga_ls8c_ard_3_yaml["id"] == actual_doc["id"]
    assert ga_ls8c_ard_3_yaml["crs"] == actual_doc["crs"]
    assert ga_ls8c_ard_3_yaml["product"]["name"] == actual_doc["product"]["name"]
    assert ga_ls8c_ard_3_yaml["label"] == actual_doc["label"]

    # Test geometry field
    doc_diff = deep_diff(
        ga_ls8c_ard_3_yaml["geometry"]["type"], actual_doc["geometry"]["type"]
    )
    assert doc_diff == {}, pformat(doc_diff)

    # Following tests will require updated package of odc_index.stac.stac_transform
    doc_diff = deep_diff(
        ga_ls8c_ard_3_yaml["geometry"]["coordinates"],
        actual_doc["geometry"]["coordinates"],
    )
    assert doc_diff == {}, pformat(doc_diff)

    # Test grids field
    doc_diff = deep_diff(ga_ls8c_ard_3_yaml["grids"], actual_doc["grids"])
    assert doc_diff == {}, pformat(doc_diff)

    # Test measurements field
    doc_diff = deep_diff(ga_ls8c_ard_3_yaml["measurements"], actual_doc["measurements"])
    assert doc_diff == {}, pformat(doc_diff)


def test_odc_metadata_link(ga_ls8c_ard_3_message):
    actual_doc, uri = get_metadata_uri(
        ga_ls8c_ard_3_message, None, "STAC-LINKS-REL:odc_yaml"
    )
    assert (
        uri == "http://dea-public-data-dev.s3-ap-southeast-2.amazonaws.com/"
        "analysis-ready-data/ga_ls8c_ard_3/088/080/2020/05/25/"
        "ga_ls8c_ard_3-1-0_088080_2020-05-25_final.odc-metadata.yaml"
    )


# Following tests will require updated package of odc_index.stac.stac_transform
# def test_stac_link(ga_ls8c_ard_3_message):
#     metadata, uri = get_metadata_uri(ga_ls8c_ard_3_message, stac_transform, None)
#     assert uri != "http://dea-public-data-dev.s3-ap-southeast-2.amazonaws.com/" \
#                   "analysis-ready-data/ga_ls8c_ard_3/088/080/2020/05/25/" \
#                   "ga_ls8c_ard_3-1-0_088080_2020-05-25_final.odc-metadata.yaml"
#     assert uri == "http://dea-public-data-dev.s3-ap-southeast-2.amazonaws.com/" \
#                   "analysis-ready-data/ga_ls8c_ard_3/088/080/2020/05/25/" \
#                   "ga_ls8c_ard_3-1-0_088080_2020-05-25_final.stac-item.json"

# def test_transform(ga_ls8c_ard_3_message, ga_ls8c_ard_3_yaml):
#     actual_doc, uri = get_metadata_uri(ga_ls8c_ard_3_message, stac_transform, None)
#
#     assert ga_ls8c_ard_3_yaml['id'] == actual_doc['id']
#     assert ga_ls8c_ard_3_yaml['crs'] == actual_doc['crs']
#     assert ga_ls8c_ard_3_yaml['product']['name'] == actual_doc['product']['name']
#     assert ga_ls8c_ard_3_yaml['label'] == actual_doc['label']
#
#     # Test geometry field
#     doc_diff = deep_diff(ga_ls8c_ard_3_yaml['geometry']['type'], actual_doc['geometry']['type'])
#     assert doc_diff == {}, pformat(doc_diff)
#
#
#     doc_diff = deep_diff(ga_ls8c_ard_3_yaml['geometry']['coordinates'], actual_doc['geometry']['coordinates'])
#     assert doc_diff == {}, pformat(doc_diff)
#
#     # Test grids field
#     doc_diff = deep_diff(ga_ls8c_ard_3_yaml['grids'], actual_doc['grids'])
#     assert doc_diff == {}, pformat(doc_diff)
#
#     # Test measurements field
#     doc_diff = deep_diff(ga_ls8c_ard_3_yaml['measurements'], actual_doc['measurements'])
#     assert doc_diff == {}, pformat(doc_diff)
#
#     # Test all fields
#     # doc_diff = deep_diff(ga_ls8c_ard_3_yaml, actual_doc)
#     # assert doc_diff == {}, pformat(doc_diff)


@pytest.fixture
def ga_ls8c_ard_3_message():
    with TEST_DATA_FOLDER.joinpath(LANDSAT_C3_SQS_MESSAGE).open("r") as f:
        body = json.load(f)
    metadata = json.loads(body["Message"])
    return metadata


@pytest.fixture
def ga_ls8c_ard_3_yaml():
    metadata = yield from documents.load_documents(
        TEST_DATA_FOLDER.joinpath(LANDSAT_C3_ODC_YAML)
    )
    return metadata
