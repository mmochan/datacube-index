#!/usr/bin/env python3
"""Index datasets found from an SQS queue into Postgres
"""
import json
import logging
import sys
from typing import Tuple

import boto3
import click
from datacube import Datacube
from datacube.index.hl import Doc2Dataset
from odc.index.stac import stac_transform


def queue_to_odc(
    queue, dc: Datacube, products: list, transform=None, limit=None, **kwargs
) -> Tuple[int, int]:

    ds_added = 0
    ds_failed = 0

    queue_empty = False

    while not queue_empty and (not limit or ds_added + ds_failed < limit):
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

            uri = None
            for link in metadata.get("links"):
                rel = link.get("rel")
                if rel and rel == "self":
                    uri = link.get("href")

            if transform:
                metadata = transform(metadata)

            doc2ds = Doc2Dataset(dc.index, **kwargs)

            if uri is not None:
                ds, err = doc2ds(metadata, uri)
                if ds is not None:
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

    return ds_added, ds_failed


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
@click.argument("queue_name", type=str, nargs=1)
@click.argument("product", type=str, nargs=1)
def cli(
    skip_lineage,
    fail_on_missing_lineage,
    verify_lineage,
    stac,
    limit,
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
    added, failed = queue_to_odc(
        queue,
        dc,
        candidate_products,
        skip_lineage=skip_lineage,
        fail_on_missing_lineage=fail_on_missing_lineage,
        verify_lineage=verify_lineage,
        transform=transform,
        limit=limit,
    )

    print(f"Added {added} Datasets, Failed {failed} Datasets")


if __name__ == "__main__":
    cli()
