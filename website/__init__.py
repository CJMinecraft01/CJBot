from threading import Thread


def run(app):
    Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start()
    print("Started website")
