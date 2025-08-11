import os
from dotenv import load_dotenv
load_dotenv(".env")

class RedmineState:
    user_id: str = os.getenv("REDMINE_USER_ID", 1)
    redmine_url: str = os.getenv("REDMINE_URL", "http://localhost:3000")
    redmine_api_key: str = os.getenv("REDMINE_API_KEY", "")
    paths: list = [
        "issues",
        "projects",
        "users",
        "time_entries",
        "wiki",
    ]