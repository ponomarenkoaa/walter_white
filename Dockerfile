FROM python:3.7-slim

RUN mkdir -p /usr/bin/app
WORKDIR /usr/bin/app

ADD /fresser /usr/bin/app/fresser

ENTRYPOINT ["python","fresser/main.py"]
