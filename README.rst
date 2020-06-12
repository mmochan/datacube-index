Datacube Index
==============

.. image:: https://github.com/opendatacube/datacube-index/workflows/Lint%20and%20Test%20Code/badge.svg?branch=master
        :target: https://github.com/opendatacube/datacube-index/actions?query=workflow%3A%22Lint+and+Test+Code%22

This is a collection of python applications and a helper docker image used to
index data into a datacube using `odc-tools <https://github.com/opendatacube/odc-tools>`_.

The functionality is exposed in form of various **<storage backend>-to-dc** utilities
which accept URI/GLOB parameters and product name(s) to index into a default datacube.
These utilities include:


#. **s3-to-dc** : Index from S3 storage to a Datacube database.
#. **thredds-to-dc** : Index from Thredds server to a Datacube database.
#. **sqs-to-dc** : Index from SQS queue to a Datacube database.

It has code to perform the follow steps:

#. Crawl S3 to find datasets using `s3-find <https://github.com/opendatacube/odc-tools/blob/master/apps/cloud/odc/apps/cloud/s3_find.py>`_
   and produce a generator.
#. Crawl Thredds using `Thredds Crawler <https://github.com/ioos/thredds_crawler>`_
   with NCI specific defaults (overrideable).
#. Index dataset YAML's found into datacube using generator/list equivalent
   of `dc-index-from-tar <https://github.com/opendatacube/odc-tools/blob/master/apps/dc_tools/odc/apps/dc_tools/index_from_tar.py>`_
   while skipping the tar file.


Usage in Production
-------------------

Production deployments of OpenDataCube typically have follow on steps to a new product or new datasets for
an existing product getting indexed. These steps are outlined below:

#. Use `OWS Update ranges <https://datacube-ows.readthedocs.io/en/latest/usage.html#as-a-web-service-in-docker-with-layers-deployed>`_ to update layer extents for products in OWS managed tables in a separate container.
#. Use `Explorer Summary generation <https://github.com/opendatacube/datacube-explorer/blob/ea57fb18a94c9a5b7c7cd9ac4a0f7b092c761fd4/cubedash/generate.py#L140>`_ to generate summaries.
#. The 3-containers are tied together by an `Airflow DAG <https://airflow.apache.org/docs/stable/concepts.html#dags>`_ using a `K8S Executor <https://airflow.apache.org/docs/1.10.1/kubernetes.html>`_.
#. Utilities in the 3 parts of the datacube applications/library ecosystem are
   tied together by custom Python scripts.
