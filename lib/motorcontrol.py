import threading, numbers, time
import smbus

class MotorControl:
    bus = smbus.SMBus(1)
    
    motorList = []
    '''
    motorList layout:
        [{"address": ___, "speed": ___}, ... ]
        
    address: I2c address of the motor
    speed: Speed of the motor
    '''
    
    def motorSpeedWrite(self, i2cAddress, speed):
    	self.bus.write_word_data(i2cAddress, 0x00, speed)
    
    def __init__(self, addressList):
        # Saving addressList
        for ii in addressList:
            if not isinstance(ii, numbers.Number):
                raise ValueError("The array input \"addressList\" needs to contain only numbers")
                
            self.motorList.append({"address":ii,"speed":0})
                
        # Main control thread
        def mainControl(self):
        	while True:
	            # Write to motors here (Make sure to write regularly)
	            for ii in self.motorList:
	                self.motorSpeedWrite(ii[0], ii[1])
                    time.sleep(200)
        
        # Setting up thread object
        threading.Thread(target=mainControl, args=[self], daemon=True).start()
    
    def setSpeed(self, *args):
        # ==============VALUE CHECKING============#
        # Checking that the speed values are actually a number
        for ii in args:
            if not isinstance(ii, numbers.Number):
                raise ValueError("Atleast one of the speed values are not numbers")
        
        # Checking that the number of speed values is the same as number of motors
        if not len(args)==len(self.motorList):
            raise ValueError('Please supply the same amount of speed values as motors ('
                + len(self.addressList) + ')')
        
        # If it passes the tests:
        # Writes speed values to motorList variable
        for ii in range(args):
            self.motorList[ii][1] = args[ii]