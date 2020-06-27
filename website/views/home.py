from flask import Blueprint

home = Blueprint('home', __name__)

@home.route("/")
def homepage():
    return "Hello world"