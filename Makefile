
run-appliance:
	docker-compose up --build --remove-orphans --force-recreate

trigger-test:
	docker-compose exec mendeleev cp -R /usr/bin/app/tests/resources/trigger /usr/bin/app/data_input/
