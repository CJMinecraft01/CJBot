def register(app):
    from .home import home

    app.register_blueprint(home)

    from .api import api_blueprint

    app.register_blueprint(api_blueprint, url_prefix="/api")
