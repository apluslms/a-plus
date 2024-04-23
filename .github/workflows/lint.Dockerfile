FROM python:3.10-bookworm

WORKDIR /app

RUN apt update && apt install -y git gcc musl-dev libffi-dev

RUN adduser --disabled-password prospector \
    && chown -R prospector:prospector /app \
    && rm -rf ${HOME}/.cache/ ${HOME}/.local/bin/__pycache__/
USER prospector

ENV PATH /home/prospector/.local/bin:${PATH}


COPY requirements.txt requirements_testing.txt /app/
RUN pip3 install --no-cache-dir --compile -r requirements_testing.txt -r requirements.txt
RUN rm /app/requirements.txt /app/requirements_testing.txt
