import awsgi2

from app.main import app


def handler(event, context):
    return awsgi2.response(app, event, context)
