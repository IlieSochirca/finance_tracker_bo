FROM python:3.8-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG 0
ENV PORT=$PORT

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT









# ==========================================================================================

# https://testdriven.io/blog/deploying-django-to-heroku-with-docker/
# https://stackoverflow.com/questions/65981042/host-an-api-on-heroku-using-a-manual-docker-build

# ==========================================================================================