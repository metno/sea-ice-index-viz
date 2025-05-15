# syntax=docker/dockerfile:1
FROM python:3.13.3
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

EXPOSE 7000

COPY /bokeh-app /bokeh-app

COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

