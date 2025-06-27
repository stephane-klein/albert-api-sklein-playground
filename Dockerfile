FROM ghcr.io/open-webui/pipelines:git-adec657

COPY ./requirements-openwebui-pipelines.txt /app/requirements-custom.txt

RUN pip install -r /app/requirements-custom.txt
