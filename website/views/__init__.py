def register(app):
    from .home import home

    app.register_blueprint(home)
