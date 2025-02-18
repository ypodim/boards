import digitalio
import board
import analogio
import time
import busio
import adafruit_mcp9808

class UnlatchingRelay:
    def __init__(self):
        self.relay_set = digitalio.DigitalInOut(board.D9)
        self.relay_unset = digitalio.DigitalInOut(board.D10)
        self.relay_set.direction = digitalio.Direction.OUTPUT
        self.relay_unset.direction = digitalio.Direction.OUTPUT
        self.relay_set.value = False
        self.relay_unset.value = False
        self.state = False
        self.toggle(False, forced=True) # forced unset
    def toggle(self, state: bool, forced=False):
        if not forced and state == self.state:
            return

        if state == True:
            self.relay_set.value = True
            time.sleep(0.01)
            self.relay_set.value = False
        else: 
            self.relay_unset.value = True
            time.sleep(0.01)
            self.relay_unset.value = False

        self.state = state

    def set(self):
        self.toggle(True)
    def unset(self):
        self.toggle(False)

class Temperature:
    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.mcp = adafruit_mcp9808.MCP9808(i2c)
        self.last_tstamp = 0
        self.last_read = 0
    def get(self):
        now = time.monotonic()
        if now - self.last_tstamp > 1:
            self.last_tstamp = now
            self.last_read = self.mcp.temperature
            # print(self.last_read, type(self.last_read))
        return self.last_read

class Manager:
    def __init__(self):
        self.pot = analogio.AnalogIn(board.A0)
        self.threshold = 0
        self.temp_low = 0
        self.temp_high = 0

    def set_temp_range(self, mid_temp, temp_range=10):
        self.temp_low = mid_temp - temp_range
        self.temp_high = mid_temp + temp_range
        print("set temp range to: %s-%s" % (self.temp_low, self.temp_high))

    def read_pot(self):
        val = self.pot.value/65536
        if abs(self.threshold - val) > 0.02:
            self.threshold = val
            # print("threshold now: %s" % self.threshold)
            # print("new temp threshold: %s" % self.get_temp_threshold())
    def get_temp_threshold(self):
        temp_range = self.temp_high - self.temp_low
        val = self.temp_low + temp_range * self.threshold
        return val


def run():
    relay = UnlatchingRelay()
    temp = Temperature()
    manager = Manager()
    manager.set_temp_range(temp.get())

    while 1:
        manager.read_pot()
        if temp.get() > manager.get_temp_threshold():
            relay.set()
        else: 
            relay.unset()
        
        time.sleep(0.001)

if __name__=="__main__":
    run()



