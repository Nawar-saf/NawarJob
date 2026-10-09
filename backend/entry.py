from fastapi.staticfiles import StaticFiles
from backend.main import app

# Public static files are mounted last so API and admin routes take precedence.
app.mount("/", StaticFiles(directory="/app/static", html=True), name="public")
