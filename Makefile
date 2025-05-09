.PHONY: build up down logs flog

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

flog:
	docker-compose logs -f frontend
