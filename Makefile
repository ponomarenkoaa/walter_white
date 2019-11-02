
run-app:
	docker build -t fresser .
	docker run -it fresser

run-app-local:
	python fresser/main.py /Users/renarde/Downloads/projects/walter_white/tmp

run-trigger:
	rm -rf /Users/anna.ponomarenko/Work/walter_white_project/CLER_HCl/trigger
	cp -R /Users/anna.ponomarenko/Work/walter_white_project/trigger /Users/anna.ponomarenko/Work/walter_white_project/CLER_HCl

