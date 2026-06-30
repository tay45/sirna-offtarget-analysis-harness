FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir .
CMD ["sirna-offtarget", "run", "--config", "examples/synthetic/config.yaml"]
