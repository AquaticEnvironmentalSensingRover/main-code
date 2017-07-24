from rover.rover import AESRover

if __name__ == '__main__':
    r = AESRover(thruster_control=True)
    r.run()
