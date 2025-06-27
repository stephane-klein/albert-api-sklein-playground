FROM ghcr.io/open-webui/pipelines:git-adec657

COPY ./requirements.txt /app/requirements-custom.txt

RUN pip install -r /app/requirements-custom.txt
