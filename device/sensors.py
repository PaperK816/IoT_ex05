import json
import time
import random
import os
import sys
import paho.mqtt.client as mqtt

# Add root directory to sys.path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class GreenhouseSensorDevice:
    def __init__(self, device_id='greenhouse_01'):
        self.device_id = device_id
        self.client_id = f'{config.MQTT_CLIENT_ID_PREFIX}{self.device_id}_{random.randint(1000, 9999)}'
        self.client = mqtt.Client(client_id=self.client_id)
        
        if config.MQTT_USERNAME and config.MQTT_PASSWORD:
            self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
            
        if os.path.exists(config.MQTT_CA_CERTS):
            self.client.tls_set(ca_certs=config.MQTT_CA_CERTS)
            
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f'[SensorDevice] Connected to MQTT Broker successfully! (rc={rc})')
            # Subscribe to control command topic
            cmd_topic = f'iot/greenhouse/{self.device_id}/command'
            client.subscribe(cmd_topic)
            print(f'[SensorDevice] Subscribed to topic: {cmd_topic}')
        else:
            print(f'[SensorDevice] Failed to connect, return code {rc}')

    def on_publish(self, client, userdata, mid):
        pass

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            print(f'[SensorDevice] Received command on {msg.topic}: {payload}')
            data = json.loads(payload)
            # Handle actuator command (e.g., irrigation switch)
            if 'action' in data:
                action = data['action']
                val = data.get('value', 'N/A')
                print(f'==> [Actuator Triggered] Action: {action}, Value: {val}')
        except Exception as e:
            print(f'[SensorDevice] Error parsing message: {e}')

    def generate_sensor_data(self):
        # Simulate realistic agricultural greenhouse data
        return {
            'device_id': self.device_id,
            'timestamp': int(time.time()),
            'soil_temperature': round(random.uniform(18.0, 28.0), 2),      # Soil Temp (°C)
            'soil_moisture': round(random.uniform(30.0, 70.0), 2),        # Soil Moisture (%)
            'air_temperature': round(random.uniform(20.0, 35.0), 2),      # Air Temp (°C)
            'air_humidity': round(random.uniform(40.0, 85.0), 2),         # Air Humidity (%)
            'light_intensity': round(random.uniform(1000.0, 50000.0), 2), # Light (lux)
            'co2_concentration': round(random.uniform(400.0, 1200.0), 2)  # CO2 (ppm)
        }

    def start(self):
        print(f'[SensorDevice] Connecting to {config.MQTT_BROKER}:{config.MQTT_PORT}...')
        try:
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
            self.client.loop_start()
            
            topic = f'iot/greenhouse/{self.device_id}/sensors'
            print(f'[SensorDevice] Start publishing sensor data to {topic} every 5 seconds...')
            
            while True:
                data = self.generate_sensor_data()
                payload = json.dumps(data)
                self.client.publish(topic, payload, qos=1)
                print(f'[Published] {payload}')
                time.sleep(5)
        except KeyboardInterrupt:
            print('[SensorDevice] Stopping sensor device...')
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f'[SensorDevice] Connection error: {e}')

if __name__ == '__main__':
    sensor_device = GreenhouseSensorDevice()
    sensor_device.start()

