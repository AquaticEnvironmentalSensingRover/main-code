from flask import Flask
import threading
from flask_socketio import SocketIO

class DataWebserver:
    flaskApp = Flask(__name__)
    app = SocketIO(flaskApp)
    
    def __init__(self):
        def startServer(self):
            self.app.run()
        
        threading.Thread(target=startServer, args=[self], daemon=True).start()
        
    @app.route("/")
    def mainPage():
        return "hello"