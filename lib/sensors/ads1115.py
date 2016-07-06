import sensor
import time

class ADS1115(sensor.Sensor):
    '''Library for the Adafruit ADS1115 ADC'''
    
    _DEFAULT_I2C_ADDRESS = 0x48
    
    def __init__(self, i2cAddress= _DEFAULT_I2C_ADDRESS, *args, **kwargs):
        super(ADS1115, self).__init__(i2cAddress, *args, **kwargs)
    
    def read(self):
        dataRate = 128
        # Write two bytes to the config register 
        self.bus.write_word_data(self.i2cAddress, 0x01, 0b0100000010000011)
        # This config: Enables continuos conversion, Disables comparator,
        # Sets the analog voltage range to 0 - 6V, and much more!
        # https://cdn-shop.adafruit.com/datasheets/ads1115.pdf (18-19)        
        
        # Wait for the ADC sample to finish based on the sample rate plus a
        # small offset to be sure (0.1 millisecond).
        time.sleep(1.0/dataRate+0.0001)
        
        # Read two bytes from register 00, the ADC value
        value = self.bus.read_word_data(self.i2cAddress, 0x00) & 0xFFFF
        # Swap byte order from little endian to big endian
        value = ((value & 0xFF) << 8) | (value >> 8)
        return value