import os
import adafruit_connection_manager
import wifi
import adafruit_requests
import digitalio
import board
import analogio
import busio
import time
import neopixel
import json
import socketpool
import microcontroller

import adafruit_mcp9808


import ssl
import adafruit_minimqtt.adafruit_minimqtt as MQTT

class Comms:
    def connect(self):
        ssid = os.getenv("CIRCUITPY_WIFI_SSID")
        password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

        pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
        self.requests = adafruit_requests.Session(pool, ssl_context)
        # rssi = wifi.radio.ap_info.rssi

        try:
            wifi.radio.connect(ssid, password)
            return 1
        except OSError as e:
            print(f"❌ OSError: {e}")
            return 0
    def send(self, message):
        JSON_POST_URL = "http://192.168.1.124:8888/closet"
        json_data = dict(msg=message)
        try:
            with self.requests.post(JSON_POST_URL, json=json_data) as response:
                json_resp = response.json()
                # Parse out the 'json' key from json_resp dict.
                print(f" | ✅ JSON 'key':'value' Response: {json_resp}")
            return 0 
        except:
            return 1
    def setup(self):
        ret = self.connect()
        while not ret:
            time.sleep(1)
            print("wifi failed, trying again.")
            ret = self.connect()

        if ret:
            pixel.signal_blue()
            print("connected to wifi")
        else:
            pixel.signal_red() 
            print("SHIT")

class Pixel:
    def __init__(self):
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)

    def signal_blue(self):
        self.pixels.fill((0, 0, 100))
        time.sleep(1)
    def signal_red(self):
        self.pixels.fill((100, 0, 0))
        time.sleep(1)
    def signal_green(self):
        self.pixels.fill((0, 100, 0))

    def blink(self, error=0):
        time.sleep(0.05)
        if error:
            self.pixels.fill((100, 10, 0))
        else:
            self.pixels.fill((0, 10, 0))
        time.sleep(0.05)
        self.pixels.fill((0, 0, 0))

# class Sensor1:
#     def __init__(self):
#         # self.adc = analogio.AnalogIn(board.A3)
#         self.uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=0.1)
#         self.uart.write(b"l")
#     def get(self):
#         self.uart.write(b"j")
#         ret = self.uart.read()
#         if ret:
#             ret = json.loads(ret.decode("utf-8"))
#             ret["tstamp"] = time.monotonic()
#             return ret
#         else:
#             return None
# class Sensor2:
#     def __init__(self):
#         self.adc = analogio.AnalogIn(board.A3)
#     def get(self):
#         return self.adc.value/65536 
class Thermo_sensor:
    def __init__(self):
        i2c = board.STEMMA_I2C()
        self.mcp = adafruit_mcp9808.MCP9808(i2c)
    def get(self):
        tempC = self.mcp.temperature
        tempF = tempC * 9 / 5 + 32
        return tempF

class RSSI_sensor:
    def __init__(self):
        pass
    def get(self):
        return wifi.radio.ap_info.rssi



class Feed:
    def __init__(self):
        self.sensors = []

        comms = Comms()
        comms.setup()

        pool = socketpool.SocketPool(wifi.radio)
        ssl_context = ssl.create_default_context()

        self.mqtt_client = MQTT.MQTT(
            broker="homeassistant.local",
            port=1883,
            username="mqtt_user",
            password="mqtt_user",
            socket_pool=pool,
            ssl_context=ssl_context,
        )
        self.mqtt_client.on_connect = self.connected
        self.mqtt_client.on_disconnect = self.disconnected
        self.mqtt_client.on_message = self.message
    def connect(self):
        self.mqtt_client.connect()

    def add_sensor(self, sensor, feed_name):
        self.sensors.append(dict(sensor=sensor, feed_name=feed_name))

    def publish(self):
        for sensor in self.sensors:
            feed = sensor["feed_name"]
            val = sensor["sensor"].get()
            self.mqtt_client.publish(feed, val)
        # self.mqtt_client.publish(self.soil, json.dumps(val), retain=True)
        # self.mqtt_client.publish(self.temp, temp)
        # self.mqtt_client.publish(self.rssi, rssi)

    def connected(self, client, userdata, flags, rc):
        print(f"Connected to HA feed")
        # Subscribe to all changes on the onoff_feed.
        for sensor in self.sensors:
            feed = sensor["feed_name"]
            client.subscribe(feed)

    def disconnected(self, client, userdata, rc):
        print("Disconnected HA feed!")

    def message(self, client, topic, message):
        print(f"New message on topic {topic}: {message}")


last_read = 0
pixel = Pixel()

feed = Feed()
feed.add_sensor(Thermo_sensor(), "/feeds/temp/1")
feed.add_sensor(RSSI_sensor(), "/feeds/rssi/1")

print("Connecting to broker...")
mqtt_connected = False
while not mqtt_connected:
    try:
        feed.connect()
        mqtt_connected = True
    except:
        print("MQTT broker not found - internet down?")
        time.sleep(1)
        pixel.blink(1)
        microcontroller.reset()


while 1:
    now = time.monotonic()
    try:
        feed.mqtt_client.loop(timeout=1)
    except:
        print("couldn't loop")
        continue

    if now - last_read > 1:        
        try:
            feed.publish()
        except:
            print("problem trying to publish - internet down?")
            # time.sleep(10)
            # microcontroller.reset()
            continue

        pixel.blink(0)
        last_read = now

