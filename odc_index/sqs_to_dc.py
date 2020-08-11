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
from ruamel.yaml import YAML
from datacube import Datacube
from datacube.index.hl import Doc2Dataset
from datacube.utils import changes
from odc.index.stac import stac_transform


def queue_to_odc(
    queue,
    dc: Datacube,
    products: list,
    transform=None,
    limit=None,
    update=False,
    archive=False,
    allow_unsafe=False,
    **kwargs,
) -> Tuple[int, int]:

    ds_added = 0
    ds_updated = 0
    ds_archived = 0
    ds_failed = 0

    queue_empty = False

    while not queue_empty and (not limit or ds_added + ds_updated + ds_archived + ds_failed < limit):
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
                ids = [uuid.UUID(metadata.get("id"))]

                if ids:
                    dc.index.datasets.archive(ids)
                    ds_archived += 1
                else:
                    logging.error("Archive skipped as failed to get ID")
                    ds_failed += 1
            else:
                metadata_uri = None
                uri = None
                for link in metadata.get("links"):
                    rel = link.get("rel")
                    if rel and rel == "derived_from":
                        metadata_uri = link.get("href")
                    elif rel and rel == "self":
                        uri = link.get("href")

                if metadata_uri:
                    metadata = YAML().load(requests.get(metadata_uri).content)
                    uri = metadata_uri
                elif transform:
                    metadata = transform(metadata)

                doc2ds = Doc2Dataset(dc.index, **kwargs)

                if uri is not None:
                    ds, err = doc2ds(metadata, uri)
                    if ds is not None:
                        if update:
                            updates = {}
                            if allow_unsafe:
                                updates = {tuple(): changes.allow_any}
                            dc.index.datasets.update(ds, updates_allowed=updates)
                            ds_updated += 1
                        else:
                            dc.index.datasets.add(ds)
                            ds_added += 1
                    else:
                        logging.error(f"Error parsing dataset {uri} with error {err}")
                        ds_failed += 1
                else:
                    logging.error("Failed to get URI from metadata doc")
                    ds_failed += 1
            # Success, so delete the message.
            message.delete()
        else:
            logging.info("No more messages...")
            queue_empty = True

    return ds_added, ds_updated, ds_archived, ds_failed


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
    "--archive",
    is_flag=True,
    default=False,
    help="If set, archive datasets",
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
    added, updated, archived, failed = queue_to_odc(
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
    )

    print(f"Added {added} Dataset(s), Updated {updated} Dataset(s), Archived {archived} Dataset(s), Failed {failed} Dataset(s)")


if __name__ == "__main__":
    cli()
