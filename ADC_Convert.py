from aesrdevicelib.sensors.ads1115 import ADS1115

x = ADS1115()

while True:
    a = x.read() #reads ADC
    c = a * (5/26665.8528646) #Converts to a 0-5V range
    output = (c * 4.444) - .4444 #Converts to mg/L based of Vernier's scale
    print(output, a)
