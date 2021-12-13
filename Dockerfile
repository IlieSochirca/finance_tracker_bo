FROM python:3.8-alpine
WORKDIR /app

# ARG definition
ARG TG_TOKEN
ARG SERVICE_ACCOUNT
ARG USER_ID

ENV tg_token=$TG_TOKEN
ENV service_account=$SERVICE_ACCOUNT
ENV user_id=$USER_ID

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG 0
ENV PORT=$PORT

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT


# ==========================================================================================

# https://testdriven.io/blog/deploying-django-to-heroku-with-docker/
# https://stackoverflow.com/questions/65981042/host-an-api-on-heroku-using-a-manual-docker-build

# ==========================================================================================