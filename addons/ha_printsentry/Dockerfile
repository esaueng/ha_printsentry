FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ha_printsentry
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8000
CMD [ "/run.sh" ]
