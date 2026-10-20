import json
import time
import random
import os
import sys
import paho.mqtt.client as mqtt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class GreenhouseSensorDevice:
    def __init__(self, device_id='greenhouse_01'):
        self.device_id = device_id
        self.client_id = f'{config.CLIENT_ID}_{random.randint(1000, 9999)}'
        self.client = mqtt.Client(client_id=self.client_id)
        
        if config.USERNAME and config.PASSWORD:
            self.client.username_pw_set(config.USERNAME, config.PASSWORD)
            
        if os.path.exists(config.CA_CERTS):
            self.client.tls_set(ca_certs=config.CA_CERTS)
            
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f'[SensorDevice] 连接 MQTT 代理成功! (rc={rc})')
            client.subscribe(config.TOPIC_COMMAND)
            print(f'[SensorDevice] 已成功订阅主题: {config.TOPIC_COMMAND}')
        else:
            print(f'[SensorDevice] 连接失败，返回码 {rc}')

    def on_publish(self, client, userdata, mid):
        pass

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            print(f'[SensorDevice] 收到来自 {msg.topic} 的控制指令: {payload}')
            data = json.loads(payload)
            if 'action' in data:
                action = data['action']
                val = data.get('value', 'N/A')
                print(f'==> [执行器触发] 动作: {action}, 参数值: {val}')
        except Exception as e:
            print(f'[SensorDevice] 解析消息出错: {e}')

    def generate_sensor_data(self):
        # 扩展的农业大棚多模态监测数据（传感器、虫情、无人机、摄像头）
        drone_statuses = ['巡检中', '待命返航', '空中悬停', '充电中']
        diseases = ['无异常', '轻度叶斑病', '白粉病预防', '蚜虫迹象']

        return {
            'device_id': self.device_id,
            'timestamp': int(time.time()),
            # 基础环境与土壤参数
            'soil_temperature': round(random.uniform(18.0, 28.0), 2),  # 土壤温度 (°C)
            'soil_moisture': round(random.uniform(30.0, 70.0), 2),  # 土壤湿度 (%)
            'air_temperature': round(random.uniform(20.0, 35.0), 2),  # 空气温度 (°C)
            'air_humidity': round(random.uniform(40.0, 85.0), 2),  # 空气湿度 (%)
            'light_intensity': round(random.uniform(1000.0, 50000.0), 2),  # 光照强度 (lux)
            'co2_concentration': round(random.uniform(400.0, 1200.0), 2),  # 二氧化碳浓度 (ppm)
            # 新增农业专属监测指标（对应实验要求 1）
            'pest_density': round(random.uniform(0.0, 15.0), 1),  # 虫情密度 (只/平方米)
            'drone_status': random.choice(drone_statuses),  # 无人机巡检状态
            'drone_disease_detected': random.choice(diseases),  # 无人机图像识别病害
            'camera_snapshot': f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"  # 摄像头抓拍记录
        }

    def start(self):
        print(f'[SensorDevice] 正在连接至 {config.BROKER_HOST}:{config.BROKER_PORT}...')
        try:
            self.client.connect(config.BROKER_HOST, config.BROKER_PORT, keepalive=60)
            self.client.loop_start()
            
            print(f'[SensorDevice] 开始定时向主题 {config.TOPIC_TELEMETRY} 上报传感器数据...')
            
            while True:
                data = self.generate_sensor_data()
                payload = json.dumps(data)
                self.client.publish(config.TOPIC_TELEMETRY, payload, qos=1)
                print(f'[已上报数据] {payload}')
                time.sleep(5)
        except KeyboardInterrupt:
            print('[SensorDevice] 正在停止传感器设备...')
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f'[SensorDevice] 连接发生错误: {e}')

if __name__ == '__main__':
    sensor_device = GreenhouseSensorDevice()
    sensor_device.start()
