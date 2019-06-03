FROM opendatacube/wms:latest

# Install C version of PyYaml
RUN apt-get update && apt-get install -y --no-install-recommends \
  libyaml-dev \
  && rm -rf /var/lib/apt/lists/* && \
  pip3 --no-cache-dir install --verbose --force-reinstall -I pyyaml

# Ensure compatible versions of boto are installed
RUN pip3 --no-cache-dir install -U 'aiobotocore[awscli,boto3]' google-cloud-storage

RUN pip3 --no-cache-dir install -U thredds_crawler

# Install dea proto for indexing tools
COPY assets/update_ranges.sh /code/index/indexing/update_ranges.sh
COPY assets/update_ranges_wrapper.sh /code/index/indexing/update_ranges_wrapper.sh
COPY assets/create-index.sh /code/index/create-index.sh
COPY assets/get_wms_config.sh /code/index/get_wms_config.sh
