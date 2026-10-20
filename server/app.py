import threading
import json
import time
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paho.mqtt.client as mqtt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

app = FastAPI(title='农业物联网监测平台 API', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

latest_telemetry = {
    'status': 'waiting_for_data',
    'timestamp': None
}
data_lock = threading.Lock()
mqtt_client = None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('[Server MQTT] 后端 MQTT 客户端连接成功!')
        client.subscribe(config.TOPIC_TELEMETRY)
        print(f'[Server MQTT] 已订阅上报主题: {config.TOPIC_TELEMETRY}')
    else:
        print(f'[Server MQTT] 连接失败，错误码 {rc}')

def on_message(client, userdata, msg):
    global latest_telemetry
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        with data_lock:
            latest_telemetry = data
        print(f'[Server MQTT] 收到遥测数据: {data}')
    except Exception as e:
        print(f'[Server MQTT] 处理遥测数据出错: {e}')

def start_mqtt_background_thread():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id='agri_server_backend')
    if config.USERNAME and config.PASSWORD:
        mqtt_client.username_pw_set(config.USERNAME, config.PASSWORD)
    if os.path.exists(config.CA_CERTS):
        mqtt_client.tls_set(ca_certs=config.CA_CERTS)
        
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        print(f'[Server MQTT] 正在连接代理 {config.BROKER_HOST}:{config.BROKER_PORT}...')
        mqtt_client.connect(config.BROKER_HOST, config.BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f'[Server MQTT] 启动后台 MQTT 线程失败: {e}')

@app.on_event('startup')
def startup_event():
    start_mqtt_background_thread()

@app.on_event('shutdown')
def shutdown_event():
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print('[Server MQTT] 后端 MQTT 客户端已断开连接。')

class CommandModel(BaseModel):
    action: str
    value: str

@app.get('/')
def read_root():
    return {'message': '欢迎使用农业物联网监测平台后端 API！'}

@app.get('/api/sensors/latest')
def get_latest_sensors():
    with data_lock:
        return latest_telemetry

@app.post('/api/control')
def send_control_command(cmd: CommandModel):
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(status_code=500, detail='MQTT 客户端未连接，无法下发指令')
    
    payload = json.dumps({'action': cmd.action, 'value': cmd.value, 'timestamp': int(time.time())})
    result = mqtt_client.publish(config.TOPIC_COMMAND, payload, qos=1)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        return {'status': 'success', 'message': '控制指令下发成功', 'command': cmd.dict()}
    else:
        raise HTTPException(status_code=500, detail='控制指令发布失败')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host=config.API_HOST, port=config.API_PORT, reload=False)
