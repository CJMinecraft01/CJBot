from threading import Thread


def run(app):
    from .views import register
    register(app)
    Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()
    print("Started website")
