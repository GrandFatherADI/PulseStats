from saleae.range_measurements import DigitalMeasurer
from math import sqrt

class RunningSD:
    def __init__(self):
        self.n = 0
        self.oldMean = 0
        self.oldSum = 0

    def add(self, value):
        self.n += 1

        if self.n < 2:
            self.oldMean = value
            self.newMean = value
            self.oldSum = 0.0
            return

        self.newMean = self.oldMean + (value - self.oldMean) / float(self.n)
        self.newSum = self.oldSum + (value - self.oldMean) * (value - self.newMean)
        self.oldMean = self.newMean
        self.oldSum = self.newSum

    def StdDev(self):
        if self.n > 1:
            return sqrt(self.newSum / float(self.n - 1))

        return 0.0

class PulseStatsMeasurer(DigitalMeasurer):
    supported_measurements = \
        ['pHMin', 'pHMax', 'pHSDev', 'pLMin', 'pLMax', 'pLSDev']

    '''
    Initialize PulseStatsMeasurer object instance. An instance is created for
    each measurement session so this code is called once at the start of each
    measurement.

    process_data(...) is then called multiple times to process data in time
    order.

    After all data has been processed measure(...) is called to complete
    analysis and return a dictionary of results.
    '''
    def __init__(self, requested_measurements):
        super().__init__(requested_measurements)
        self.pHMin = None
        self.pHMean = 0.0
        self.pHMax = None
        self.pLMin = None
        self.pLMean = 0.0
        self.pLMax = None
        self.lowPulses = 0.0
        self.highPulses = 0.0
        self.lastTime = None
        self.lastState = None
        self.HSDev = RunningSD()
        self.LSDev = RunningSD()

    '''
    process_data() will be called one or more times per measurement with batches
    of data.

    data has the following interface:

      * Iterate over data to get transitions in the form of pairs of
        `Time`, Bitstate (`True` for high, `False` for low)

    `Time` currently only allows taking a difference with another `Time`, to
    produce a `float` number of seconds
    '''
    def process_data(self, data):
        for t, bitstate in data:
            if self.lastState is None:
                self.lastState = bitstate

            if bitstate == self.lastState:
                continue

            self.lastState = bitstate

            if self.lastTime is None:
                self.lastTime = t
                continue

            timeDelta = float(t - self.lastTime)
            self.lastTime = t

            if bitstate:
                # high going edge so end of low pulse
                self.lowPulses += 1.0
                self.pLMean += timeDelta
                self.LSDev.add(timeDelta)

                if self.pLMin == None or timeDelta < self.pLMin:
                    self.pLMin = timeDelta

                if self.pLMax == None or timeDelta > self.pLMax:
                    self.pLMax = timeDelta

            else:
                # low going edge so end of high pulse
                self.highPulses += 1.0
                self.pHMean += timeDelta
                self.HSDev.add(timeDelta)

                if self.pHMin == None or timeDelta < self.pHMin:
                    self.pHMin = timeDelta

                if self.pHMax == None or timeDelta > self.pHMax:
                    self.pHMax = timeDelta

    '''
    measure(...) is called after all the relevant data has been processed by
    process_data(...). It returns a dictionary of measurement results.
    '''
    def measure(self):
        values = {}

        if self.pHMin != None:
            values['pHMin'] = self.pHMin
            values['pHMean'] = self.pHMean / self.highPulses
            values['pHMax'] = self.pHMax
            values['pHSDev'] = self.HSDev.StdDev()

        if self.pLMin != None:
            values['pLMin'] = self.pLMin
            values['pLMean'] = self.pLMean / self.lowPulses
            values['pLMax'] = self.pLMax
            values['pLSDev'] = float(self.LSDev.StdDev())

        return values
