FROM docker.io/python:3.10-alpine

WORKDIR /app

RUN apk update && apk add git freetype-dev gcc musl-dev

RUN adduser --disabled-password prospector prospector \
    && chown -R prospector:prospector /app \
    && rm -rf ${HOME}/.cache/ ${HOME}/.local/bin/__pycache__/
USER prospector

ENV PATH /home/prospector/.local/bin:${PATH}


COPY requirements.txt requirements_testing.txt /app/
RUN pip3 install --no-cache-dir --compile -r requirements_testing.txt -r requirements.txt
RUN rm /app/requirements.txt /app/requirements_testing.txt
