
run-appliance:
	docker-compose up --build

trigger-test:
	docker-compose exec walter cp -R /usr/bin/app/tests/resources/trigger /usr/bin/app/data_input


run-walter:
	docker-compose up --build walter