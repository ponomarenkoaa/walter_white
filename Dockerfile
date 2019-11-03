FROM python:3.7-slim

ENV APP_PATH=/usr/bin/app
RUN mkdir -p ${APP_PATH}
RUN mkdir -p ${APP_PATH}/data_input
WORKDIR ${APP_PATH}

ADD requirements.txt ${APP_PATH}/requirements.txt
RUN pip install -r requirements.txt
ADD /fresser ${APP_PATH}/fresser
ADD /tests ${APP_PATH}/tests

ENTRYPOINT ["python","fresser/main.py","/usr/bin/app/data_input"]
