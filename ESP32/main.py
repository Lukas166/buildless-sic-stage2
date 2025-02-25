import network
import time
import machine
import ubinascii
import json
import dht
import ssd1306
from umqtt.simple import MQTTClient
import urequests

WIFI_SSID = "chalkid"
WIFI_PASS = "1483369waddupbiatch"

UBIDOTS_TOKEN = "BBUS-Wmhmg1XVKEEsq7NND8YtODkT1w6lqU"
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_PORT = 1883
DEVICE_LABEL = "esp32_device"

LDR_PIN = 34  # LDR Sensor (Analog)
LED_PIN = 5   # LED Output
DHT_PIN = 4   # DHT11 Sensor
PIR_PIN = 14  # PIR Sensor (Gerakan) menggunakan GPIO 14
BUZZER_PIN = 18  # Buzzer

# Setup Perangkat
led = machine.Pin(LED_PIN, machine.Pin.OUT)
dht_sensor = dht.DHT11(machine.Pin(DHT_PIN))
ldr_sensor = machine.ADC(machine.Pin(LDR_PIN))
ldr_sensor.atten(machine.ADC.ATTN_11DB)
pir_sensor = machine.Pin(PIR_PIN, machine.Pin.IN)
buzzer = machine.Pin(BUZZER_PIN, machine.Pin.OUT)

# OLED Setup
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

lightInit = ldr_sensor.read()
threshold = lightInit * 0.8 

CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode()

# Koneksi WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)

    attempt = 0
    while not wlan.isconnected():
        time.sleep(2)
        attempt += 1
        print(f"Connecting to WiFi... Attempt {attempt}")
        if attempt > 10:
            print("❌ WiFi Connection Failed! Restarting...")
            machine.reset()

    print("✅ Connected to WiFi!")

# Koneksi MQTT
def connect_mqtt():
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT, user=UBIDOTS_TOKEN, password="")
        client.connect()
        print("✅ Connected to Ubidots MQTT!")
        return client
    except Exception as e:
        print(f"❌ MQTT Connection Failed: {e}")
        time.sleep(5)
        return None

# Kirim Data ke Ubidots
def publish_data(client, variable, value):
    if not client:
        print("⚠️ MQTT Client Not Connected!")
        return

    topic = f"/v1.6/devices/{DEVICE_LABEL}"
    payload = json.dumps({variable: value})

    try:
        client.publish(topic, payload)
        print(f"✅ Sent {variable}: {value}")
    except Exception as e:
        print(f"❌ Failed to Publish: {e}")

# Kirim Data ke Flask Server
def send_to_flask(data):
    url = "http://192.168.81.110:5000/data"  # Ganti dengan IP server Flask Anda
    headers = {"Content-Type": "application/json"}

    try:
        response = urequests.post(url, json=data, headers=headers)
        print("✅ Data sent to Flask:", response.text)
        response.close()
    except Exception as e:
        print("❌ Failed to send data to Flask:", str(e))

# Update OLED Display
def update_oled(ldr_value, temperature, humidity, led_status, motion_detected, screen_index):
    oled.fill(0)
    
    if screen_index == 0:
        oled.text("Light Intensity", 0, 0)
        oled.text(f"{ldr_value}", 0, 20)
    elif screen_index == 1:
        oled.text("Temperature", 0, 0)
        oled.text(f"{temperature}C", 0, 20)
    elif screen_index == 2:
        oled.text("Humidity", 0, 0)
        oled.text(f"{humidity}%", 0, 20)
    elif screen_index == 3:
        oled.text("LED Status", 0, 0)
        oled.text(f"{'ON' if led_status else 'OFF'}", 0, 20)
    elif screen_index == 4:
        oled.text("Motion Sensor", 0, 0)
        oled.text(f"{'Detected' if motion_detected else 'No Motion'}", 0, 20)

    oled.show()

# Program Utama
def main():
    connect_wifi()
    client = connect_mqtt()

    if not client:
        print("⚠️ Could not connect to MQTT, retrying in 10s...")
        time.sleep(10)
        main()

    counter = 0
    screen_index = 0

    while True:
        try:
            ldr_value = ldr_sensor.read()
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            motion_detected = pir_sensor.value()

            # Nyalakan LED jika cahaya kurang
            if ldr_value < threshold:
                led.value(1)
            else:
                led.value(0)

            led_status = led.value()

            if motion_detected:
                buzzer.value(1)
            else:
                buzzer.value(0)

            # Update OLED
            update_oled(ldr_value, temperature, humidity, led_status, motion_detected, screen_index)

            # Ganti tampilan OLED setiap 2 detik
            if counter % 2 == 0:
                screen_index = (screen_index + 1) % 5

            # Kirim data ke MQTT setiap 5 detik
            if counter % 5 == 0:
                publish_data(client, "light", ldr_value)
                publish_data(client, "temperature", temperature)
                publish_data(client, "humidity", humidity)
                publish_data(client, "led_status", led_status)
                publish_data(client, "motion", motion_detected)

                # Kirim data ke Flask Server
                sensor_data = {
                    "light": ldr_value,
                    "temperature": temperature,
                    "humidity": humidity,
                    "led_status": led_status,
                    "motion": motion_detected
                }
                send_to_flask(sensor_data)

            counter += 1
            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            client.disconnect()
            time.sleep(5)
            main()

# Jalankan Program
main()