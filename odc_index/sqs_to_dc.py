#!/usr/bin/env python3
"""Index datasets found from an SQS queue into Postgres
"""
import json
import logging
import uuid
from typing import Tuple

import boto3
import click
import requests
from datacube import Datacube
from datacube.index.hl import Doc2Dataset
from datacube.utils import changes, documents
from odc.index.stac import stac_transform


# Added log handler
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


def queue_to_odc(
    queue,
    dc: Datacube,
    products: list,
    transform=None,
    limit=None,
    update=False,
    archive=False,
    allow_unsafe=False,
    odc_metadata_link=False,
    **kwargs,
) -> Tuple[int, int]:

    ds_success = 0
    ds_failed = 0

    queue_empty = False

    doc2ds = Doc2Dataset(dc.index, **kwargs)

    while not queue_empty and (not limit or ds_success + ds_failed < limit):
        messages = queue.receive_messages(
            VisibilityTimeout=60,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            MessageAttributeNames=["All"],
        )

        if len(messages) > 0:
            message = messages[0]
            body = json.loads(message.body)
            metadata = json.loads(body["Message"])
            if archive:
                archive_success = do_archiving(metadata, dc)
                if archive_success:
                    ds_success += 1
                else:
                    ds_failed += 1
            else:

                # Extract metadata and URI for indexing/archiving
                metadata, uri = get_metadata_uri(metadata, odc_metadata_link, transform)

                # Index/archive metadata
                index_success = do_indexing(
                    metadata, uri, dc, doc2ds, update, archive, allow_unsafe
                )
                if index_success:
                    ds_success += 1
                else:
                    ds_failed += 1

            # Success, so delete the message.
            message.delete()
        else:
            logging.info("No more messages...")
            queue_empty = True

    return ds_success, ds_failed


def get_metadata_uri(metadata, odc_metadata_link, transform):
    metadata_uri = None
    uri = None
    for link in metadata.get("links"):
        rel = link.get("rel")
        if odc_metadata_link and rel and rel == "odc_yaml":
            metadata_uri = link.get("href")
        elif rel and rel == "self":
            uri = link.get("href")

    if metadata_uri:
        try:
            content = requests.get(metadata_uri).content
            metadata = documents.parse_yaml(content)
            uri = metadata_uri
        except requests.RequestException as err:
            logging.error(f"Failed to load metadata from the link provided -  {err}")
    else:
        logging.error("ODC EO3 metadata link not found")

    if transform:
        metadata = transform(metadata)

    return metadata, uri


def do_archiving(metadata, dc: Datacube):
    ds_success = False
    ids = [uuid.UUID(metadata.get("id"))]

    if ids:
        dc.index.datasets.archive(ids)
        ds_success = True
    else:
        logging.error("Archive skipped as failed to get ID")
    return ds_success


def do_indexing(
    metadata, uri, dc: Datacube, doc2ds: Doc2Dataset, update=False, allow_unsafe=False
) -> Tuple[int, int]:

    ds_success = False

    if uri is not None:
        ds, err = doc2ds(metadata, uri)
        if ds is not None:
            if update:
                updates = {}
                if allow_unsafe:
                    updates = {tuple(): changes.allow_any}
                dc.index.datasets.update(ds, updates_allowed=updates)
                ds_success = True
            else:
                dc.index.datasets.add(ds)
                ds_success = True
        else:
            logging.error(f"Error parsing dataset {uri} with error {err}")
    else:
        logging.error("Failed to get URI from metadata doc")

    return ds_success


@click.command("sqs-to-dc")
@click.option(
    "--skip-lineage",
    is_flag=True,
    default=False,
    help="Default is not to skip lineage. Set to skip lineage altogether.",
)
@click.option(
    "--fail-on-missing-lineage/--auto-add-lineage",
    is_flag=True,
    default=True,
    help=(
        "Default is to fail if lineage documents not present in the database. "
        "Set auto add to try to index lineage documents."
    ),
)
@click.option(
    "--verify-lineage",
    is_flag=True,
    default=False,
    help="Default is no verification. Set to verify parent dataset definitions.",
)
@click.option(
    "--stac",
    is_flag=True,
    default=False,
    help="Expect STAC 1.0 metadata and attempt to transform to ODC EO3 metadata",
)
@click.option(
    "--odc-metadata-link",
    is_flag=True,
    default=False,
    help="Expect metadata doc with ODC EO3 metadata link",
)
@click.option(
    "--limit",
    default=None,
    type=int,
    help="Stop indexing after n datasets have been indexed.",
)
@click.option(
    "--update",
    is_flag=True,
    default=False,
    help="If set, update instead of add datasets",
)
@click.option(
    "--archive", is_flag=True, default=False, help="If set, archive datasets",
)
@click.option(
    "--allow-unsafe",
    is_flag=True,
    default=False,
    help="Allow unsafe changes to a dataset. Take care!",
)
@click.argument("queue_name", type=str, nargs=1)
@click.argument("product", type=str, nargs=1)
def cli(
    skip_lineage,
    fail_on_missing_lineage,
    verify_lineage,
    stac,
    odc_metadata_link,
    limit,
    update,
    archive,
    allow_unsafe,
    queue_name,
    product,
):
    """ Iterate through messages on an SQS queue and add them to datacube"""

    transform = None
    if stac:
        transform = stac_transform

    candidate_products = product.split()

    sqs = boto3.resource("sqs")
    queue = sqs.get_queue_by_name(QueueName=queue_name)

    # Do the thing
    dc = Datacube()
    success, failed = queue_to_odc(
        queue,
        dc,
        candidate_products,
        skip_lineage=skip_lineage,
        fail_on_missing_lineage=fail_on_missing_lineage,
        verify_lineage=verify_lineage,
        transform=transform,
        limit=limit,
        update=update,
        archive=archive,
        allow_unsafe=allow_unsafe,
        odc_metadata_link=odc_metadata_link,
    )

    result_msg = ""
    if update:
        result_msg += f"Updated {success} Dataset(s), "
    elif archive:
        result_msg += f"Archived {success} Dataset(s), "
    else:
        result_msg += f"Added {success} Dataset(s), "
    result_msg += f"Failed {failed} Dataset(s)"
    print(result_msg)


if __name__ == "__main__":
    cli()
