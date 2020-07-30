from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import config
import logging

logging.basicConfig(format="[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s", datefmt="%H:%M:%S", level=logging.INFO)

load_dotenv()

app = Flask(__name__, template_folder="website/templates/", static_folder="website/static/")
app.config.from_object(config)

db = SQLAlchemy(app)
import models
db.create_all()
db.session.commit()


if __name__ == "__main__":
    from bot import run as start_bot
    from website import run as start_website
    start_website(app)
    start_bot()
