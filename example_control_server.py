from rover.control_server.control_server import ControlServer

if __name__ == '__main__':
    cs = ControlServer(host="0.0.0.0", port=8000)
    cs.run_server()
