DEV_DOCKERFILES=-f docker-compose.yml -f docker-compose.dev.yml

build:
	docker-compose ${DEV_DOCKERFILES} build

up:
	docker-compose ${DEV_DOCKERFILES} up

clean:
	docker-compose ${DEV_DOCKERFILES} down

init:
	docker-compose exec dc-index \
		datacube system init --no-init-users

shell:
	docker-compose exec dc-index \
		bash

product-s2-stac:
	docker-compose exec dc-index \
		datacube product add https://raw.githubusercontent.com/digitalearthafrica/config/master/products/esa_s2_l2a.yaml

index-s2-stac:
	docker-compose exec dc-index \
		python /code/odc_index/s3_to_dc.py --stac --update --allow-unsafe \
		s3://sentinel-cogs/sentinel-s2-l2a-cogs/2020/S2A_27PZT_20200601_0_L2A/*.json s2_l2a

index-s2-stac-sqs:
	docker-compose exec dc-index \
		python /code/odc_index/sqs_to_dc.py --stac --limit=10 "test_africa" s2_l2a

metadata-sandbox:
	docker-compose exec dc-index \
		datacube metadata add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/workspaces/sandbox-metadata.yaml

product-s2-nbar:
	docker-compose exec dc-index \
		datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/ga_s2_ard_nbar/ga_s2_ard_nbar_granule.yaml

index-s2-nbar-test:
	docker-compose exec dc-index \
		/code/index-sentinel-2.py --start-date 2020-06-01 --end-date 2020-07-01 "ga_s2a_ard_nbar_granule ga_s2b_ard_nbar_granule"

index-stac-api:
	docker-compose exec dc-index \
		python /code/odc_index/stac_api_to_dc.py \
		--bbox='-20,30,20,40' \
		--limit=2 \
		--collections='sentinel-s2-l2a-cogs' \
		--datetime='2020-08-01/2020-08-31' \
		s2_l2a

test-load-s2:
	docker-compose exec dc-index \
		python -c "\
import datacube;\
dc = datacube.Datacube(); \
ds = dc.find_datasets(product='s2_l2a', limit=1); \
dc.load(product='s2_l2a',id=ds[0].id,output_crs='EPSG:4326',resolution=(0.1,0.1))"

index-stac-api-au:
	docker-compose exec \
		--env STAC_API_URL=https://explorer.sandbox.dea.ga.gov.au/stac/ \
		dc-index \
		python /code/odc_index/stac_api_to_dc.py \
		--limit=10 \
		s2_l2a
	