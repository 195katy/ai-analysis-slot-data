FROM public.ecr.aws/lambda/python:3.12

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

COPY pyproject.toml uv.lock ${LAMBDA_TASK_ROOT}/
RUN cd ${LAMBDA_TASK_ROOT} && uv sync --frozen --no-dev --no-install-project

COPY app/ ${LAMBDA_TASK_ROOT}/app/

ENV PATH="${LAMBDA_TASK_ROOT}/.venv/bin:${PATH}"
ENV AWS_REGION="us-east-1"
ENV BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
ENV S3_BUCKET="slot-data-accumulation"
ENV S3_CSV_KEY="data.csv"
ENV STORAGE_TYPE="s3"
ENV LOCAL_DATA_DIR=""

CMD ["app.handler.handler"]
