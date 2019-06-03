#!/bin/bash

set -e

# Init system
datacube system init --no-init-users 2>&1

# Add product definitions to datacube
# URLS must be delimited with ':' and WITHOUT http(s)://
# Add product definitions to datacube
# URLS must be delimited with ':' and WITHOUT http(s)://
function add_products {
    mkdir -p firsttime/products

    read -ra URLS <<<"$PRODUCT_URLS"

    for U in "${URLS[@]}"
    do
        wget $U -O firsttime/products/$(cat /dev/urandom | tr -cd 'a-f0-9' | head -c 16).yaml
    done

    for file in firsttime/products/*
    do
        datacube product add "$file"
    done
}

add_products

# Generate WMS specific config
python3 ../update_ranges.py --schema 2>&1 --role $DB_ROLE || echo "Warning: Can't create schema"


#Export wms config to actual path 
get_wms_config.sh

# Run index
indexing/update_ranges_wrapper.sh

set +e
