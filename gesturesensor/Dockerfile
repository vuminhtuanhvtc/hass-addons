ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:3.12
FROM $BUILD_FROM

WORKDIR /app

RUN apk add --no-cache ffmpeg libsm6 libxext6

COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

CMD [ "python", "./gesturesensor.py" ]
