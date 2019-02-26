FROM opendatacube/wms:latest

# Ensure compatible versions of boto are installed
RUN pip3 uninstall boto3 botocore dea-proto -y && \
    pip3 install -U 'aiobotocore[awscli,boto3]' google-cloud-storage

# Install dea proto for indexing tools
RUN pip3 install -e 'git+https://github.com/opendatacube/dea-proto.git#egg=project[GCP,THREDDS]'

# Install C version of PyYaml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libyaml-dev \
    && rm -rf /var/lib/apt/lists/* && \
    pip3 --no-cache-dir install --verbose --force-reinstall -I pyyaml

COPY assets/update_ranges.sh /code/index/indexing/update_ranges.sh
COPY assets/update_ranges_wrapper.sh /code/index/indexing/update_ranges_wrapper.sh
COPY assets/create-index.sh /code/index/create-index.sh