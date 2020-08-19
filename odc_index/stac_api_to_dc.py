#!/usr/bin/env python3
"""Index datasets found from an SQS queue into Postgres
"""
import json
import logging
import sys
from typing import Tuple
import os

import click
from datacube import Datacube
from datacube.index.hl import Doc2Dataset
from datacube.utils import changes
from odc.index.stac import stac_transform
from satsearch import Search


def stac_api_to_odc(
    dc: Datacube,
    products: list,
    transform=None,
    limit=None,
    update=False,
    allow_unsafe=False,
    datetime=None,
    bbox=None,
    collections=None,
    **kwargs,
) -> Tuple[int, int]:

    ds_added = 0
    ds_failed = 0

    if bbox:
        bbox = list(map(float, bbox.split(",")))
        assert len(bbox) == 4, "bounding box must be of the form lon-min,lat-min,lon-max,lat-max"

    if collections:
        collections = collections.split(",")

    srch = Search().search(datetime=datetime, collections=collections, bbox=bbox)

    n_items = srch.found()
    print("Found {} items to index".format(n_items))

    if n_items > 0:
        doc2ds = Doc2Dataset(dc.index, **kwargs)
        if limit:
            items = srch.items(limit=limit)
        else:
            items = srch.items()
        for metadata in items.geojson()["features"]:

            # This is a horrible hack, but we want a path to the
            # data, which is probably S3... Pick the first COG
            # to use for this.
            uri = None
            if metadata.get("assets"):
                for asset in metadata["assets"].values():
                    if (
                        asset.get("type")
                        == "image/tiff; application=geotiff; profile=cloud-optimized"
                    ):
                        path = os.path.dirname(asset["href"])
                        id = os.path.basename(path)
                        uri = f"{path}/{id}.json"
                        break
            for link in metadata.get("links"):
                rel = link.get("rel")
                if rel and rel == "self":
                    if not uri:
                        uri = link.get("href")
                    else:
                        print(link.get("href"))
                    break

            if transform:
                metadata = transform(metadata)

            print(uri)

            if uri is not None:
                ds, err = doc2ds(metadata, uri)
                if ds is not None:
                    if update:
                        updates = {}
                        if allow_unsafe:
                            updates = {tuple(): changes.allow_any}
                        dc.index.datasets.update(ds, updates_allowed=updates)
                    else:
                        ds_added += 1
                        dc.index.datasets.add(ds)
                else:
                    logging.error(f"Error parsing dataset {uri} with error {err}")
                    ds_failed += 1
            else:
                logging.error("Failed to get URI from metadata doc")
                ds_failed += 1
    else:
        print("Didn't find any items, finishing.")

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
@click.option(
    "--update",
    is_flag=True,
    default=False,
    help="If set, update instead of add datasets",
)
@click.option(
    "--allow-unsafe",
    is_flag=True,
    default=False,
    help="Allow unsafe changes to a dataset. Take care!",
)
@click.option(
    "--collections",
    type=str,
    default=None,
    help="Comma separated list of collections to search",
)
@click.option(
    "--bbox",
    type=str,
    default=None,
    help="Comma separated list of bounding box coords, lon-min, lat-min, lon-max, lat-max",
)
@click.option(
    "--datetime",
    type=str,
    default=None,
    help="Dates to search, either one day or an inclusive range, e.g. 2020-01-01 or 2020-01-01/2020-01-02",
)
@click.argument("product", type=str, nargs=1)
def cli(
    skip_lineage,
    fail_on_missing_lineage,
    verify_lineage,
    stac,
    limit,
    update,
    allow_unsafe,
    collections,
    bbox,
    datetime,
    product,
):
    """ 
    Iterate through STAC items from a STAC API and add them to datacube
    Note that you need to set the STAC_API_URL environment variable to
    something like https://earth-search.aws.element84.com/v0/
    """

    transform = None
    if stac:
        transform = stac_transform

    candidate_products = product.split()

    # Do the thing
    dc = Datacube()
    added, failed = stac_api_to_odc(
        dc,
        candidate_products,
        skip_lineage=skip_lineage,
        fail_on_missing_lineage=fail_on_missing_lineage,
        verify_lineage=verify_lineage,
        transform=transform,
        limit=limit,
        update=update,
        allow_unsafe=allow_unsafe,
        datetime=datetime,
        bbox=bbox,
        collections=collections,
    )

    print(f"Added {added} Datasets, Failed {failed} Datasets")


if __name__ == "__main__":
    cli()
