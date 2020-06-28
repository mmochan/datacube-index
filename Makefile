DEV_DOCKERFILES=-f docker-compose.yml -f docker-compose.dev.yml

build:
	docker-compose ${DEV_DOCKERFILES} build

up:
	docker-compose ${DEV_DOCKERFILES} up

init:
	docker-compose exec dc-index \
		datacube system init

shell:
	docker-compose exec dc-index \
		bash

product-s2:
	docker-compose exec dc-index \
		datacube product add https://raw.githubusercontent.com/digitalearthafrica/config/master/products/esa_s2_l2a.yaml

index-s2:
	docker-compose exec dc-index \
		python /code/odc_index/s3_to_dc.py --stac --update --allow-unsafe \
		s3://sentinel-cogs/sentinel-s2-l2a-cogs/2020/S2A_27PZT_20200601_0_L2A/*.json s2_l2a

index-sqs-s2:
	docker-compose exec dc-index \
		python /code/odc_index/sqs_to_dc.py --stac --limit=10 "test_africa" s2_l2a

metadata:
	docker-compose exec dc-index \
		datacube metadata add /code/eo_plus.yaml

product-nbar:
	docker-compose exec dc-index \
		datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/ga_s2_ard_nbar/ga_s2_ard_nbar_granule.yaml

index-s2-test:
	docker-compose exec dc-index \
		/code/index-sentinel-2.py --start-date 2020-06-01 --end-date 2020-07-01 "ga_s2a_ard_nbar_granule ga_s2b_ard_nbar_granule"
