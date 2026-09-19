FROM public.ecr.aws/lambda/python:3.12

RUN pip install --no-cache-dir uv
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/
RUN uv pip install --system --no-cache -r pyproject.toml

COPY app/ ${LAMBDA_TASK_ROOT}/app/

CMD ["app.handler.handler"]
