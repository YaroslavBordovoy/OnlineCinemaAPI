from fastapi import FastAPI


app = FastAPI(
    title="Online Cinema",
    description="A digital platform that allows users to select, watch, and "
    "purchase access to movies and other video materials via the internet.",
)

api_version_prefix = "/api/v1"
