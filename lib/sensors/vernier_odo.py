import ads1115


class VernierODO(ads1115.ADS1115):
    def __init__(self, *args, **kwargs):
        self.superClass = super(VernierODO, self)
        self.superClass.__init__(*args, **kwargs)

    def convertMGL(self, volt):
        # Converts to mg/L based of Vernier's scale
        return (volt * 4.444) - .4444

    def convertPct(self, volt):
        # Converts to percentage based of Vernier's scale
        return (volt * 66.666) - 6.6666

    def read(self):
        adc = self.superClass.read()
        volt = self.superClass.asVolt(adc)

        return {'rawADC': adc, 'volt': volt, 'mgL': self.convertMGL(volt),
                'pct': self.convertPct(volt)}
