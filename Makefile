
run-appliance:
	docker-compose up --build --remove-orphans -V

trigger-test:
	docker-compose exec mendeleev cp -R /usr/bin/app/tests/resources/trigger /usr/bin/app/data_input/

connect-psql:
	docker-compose  exec postgres bash -c 'psql -U mendeleev mendeleev'