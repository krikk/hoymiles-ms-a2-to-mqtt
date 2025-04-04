FROM python:3.13-slim-bookworm

LABEL maintainer="dockerhub@badcloud.eu"
LABEL description="dest"



WORKDIR /usr/src/app

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


COPY ./ ./





CMD [ "python","-u","/usr/src/app/hoymiles-ms-a2-to-mqtt.py" ]