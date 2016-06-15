import threading, numbers, time
import motorcontrol

class Navigation:
    idle = True # If it is in "idle" mode
    targetPos = [None,None] # Target x,y position
    targetBearing = None
    atTarget = None # True when the raft is on the target position/angle
    motorConfig = None # Motor configuration
    currentPosition = [None,None] # Current position in "longitude" and "latititude"
    currentBearing = None # Current bearing in "degrees"
    
    '''
    motorConfig layout:
        [{'x':x,'y':y,'r':radius,'i2c':address}, ... ]
        
        Each motor has a set of these values:
            x: X "influence"2 factor
            y: Y "influence" factor
            ^^^ X and Y values of unit vector in direction of motor
            r: Radius from center of raft
            i2c: I2c address of the motor
            
        NOTE: RIGHT NOW, THIS LIBRARY ONLY SUPPORTS 4 MOTOR SETUPS AND THE MOTORS
            SHOULD BE SUPPLIED STARTING AT THE TOP AND GOING CLOCKWISE
    '''
    
    motors = None # MotorControl instance that directly interfaces to the motors
    
    
    #==================BEGIN Calculation Functions==========#
    
    # OLD "calculation" FUNCTIONS
    '''
    def traverseCalculate(self, x, y):
        if not isinstance(x, numbers.Number):
            raise ValueError("The input value \"x\" needs to be a number")
        if not isinstance(y, numbers.Number):
            raise ValueError("The input value \"y\" needs to be a number")
        
        
        # TODO: ADD CALCULATION
       
    def rotateCalculate(self, angle):
        if not isinstance(angle, numbers.Number):
            raise ValueError("The input value \"angle\" needs to be a number")  
        
        # TODO: ADD CALCULATION
    '''
    #==================END Calculation Functions==========#
    
    def readGPS():
        # RUN IN SEPERATE THREAD
        # READ GPS IN TRY FINALLY SO THAT IF AN ERROR HAPPENS
        # IT CAN WRITE "None"  OR ANOTHER VALUE TO "currentPosition"
        # TO POINT OUT AN ERROR HAS OCCURED
        
        pass
        
    def readCompass():
        # DO THE SAME AS GPS COMMENTS
        pass
    
    def __init__(self, motorConfig):
        #Initialising Below...
        
        if not len(motorConfig) == 4:
            raise ValueError('This library currently supports only 4 motor setups')
        
        #Check motorConfig to make sure it is complete (has every piece of info)
        for ii in motorConfig:
            '''
            if not ("x" in ii
                    and "y" in ii
                    and "r" in ii
                    and "i2c" in ii):
                raise ValueError('The motorConfig array is not complete')
            '''
            if not "i2c" in ii:
                raise ValueError('The motorConfig array is not complete')
        
        #Store motorConfig
        self.motorConfig = motorConfig
        
        addressList=[]
        for ii in self.motorConfig:
            addressList.append(ii["i2c"])
        
        #Create instance of motorcontrol
        self.motors = motorcontrol.MotorControl(addressList)
        
        #Main control thread
        def mainThread(self):
            while True:
                #==============BEGIN Motor Writing==============#
                pass
                #==============END Motor Writing==============#
            
            #TODO: Write to MotorControl instance
        
        #Setting up and starting thread
        threading.Thread(target=mainThread, args=[self], daemon=True).start()
    

        
    #MODE Selection Methods:
    '''
    Mode List:
        - Move to position (stop after reaching)
        - Hold position (until Idled)
        - Idle
    '''
    
    def move(self, x=0, y=0, bearing=0, hold=True):
        if not isinstance(x, numbers.Number):
            raise ValueError("The input \"x\" needs to be a number")
        if not isinstance(y, numbers.Number):
            raise ValueError("The input \"y\" needs to be a number")
        if not isinstance(bearing, numbers.Number):
            raise ValueError("The input \"bearing\" needs to be a number")
        if not type(hold) == type(True):
            raise ValueError("The input \"hold\" needs to be a boolean")
        
        self.idle = False
        
        # TODO: CALCULATE ACTUAL GPS LOCATION FOR TARGET
        
        self.targetPos = [self.currentPosition[0] + x, self.currentPosition[1] + y]
        
        self.targetBearing = bearing
        
        self.atTarget = False
        if hold==False:
            while not self.atTarget:
                time.sleep(200)
    
    
    # OLD "move" functions:
    '''
    def move(self, x, y, hold=False):
        if hold:
            self.mode = "moveHold"
        else:
            self.mode = "move"
        
        if not (isinstance(x, numbers.Number)
                and isinstance(y, numbers.Number)):
            raise ValueError("Either \"x\" or \"y\" is not a number")
            
        self.targetPos = [x,y]
        
        # TODO: HOLD HERE UNTIL "atTarget" IS "True" IF "hold" IS "True"
        
    def rotate(self, hold, angle=None, bearing=None):
        # Checking that atleast one of them are set:
        if angle==None and bearing==None:
            raise ValueError("Please supply a \"angle\" or \"bearing\" value")
        
        # Checking that both aren't set:
        else:
            if (not angle==None) and (not bearing==None):
                raise ValueError("Please only supply a \"angle\" or \"bearing\" value")
            
            else:
                if not angle==None:
                    # If angle is the used variable:
                    # Check if it is a number
                    if isinstance(angle, numbers.Number):
                        # Set mode variable according to whether it is on hold mode
                        if hold:
                            self.mode = "angle"
                        else:
                            self.mode = "angleHold"
                        # TODO: CALCULATE "self.targetBearing" FROM
                        # CURRENT BEARING AND "angle"
                        self.targetPos = [None,None]
                    else:
                        raise ValueError("The input \"angle\" is not a number")
                
                if not bearing==None:
                    # If bearing is the used variable:
                    # Check if it is a number
                    if isinstance(angle, numbers.Number):
                        # Set mode variable according to whether it is on hold mode
                        if hold:
                            self.mode = "bearing"
                        else:
                            self.mode = "bearingHold"
                        self.targetBearing = bearing
                        self.targetPos = [None,None]
                    else:
                        raise ValueError("The input \"bearing\" is not a number")
    '''