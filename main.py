from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import config

load_dotenv()

app = Flask(__name__)
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
