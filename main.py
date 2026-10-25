import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# Ваши ключи из проекта ESP32
SINRIC_API_KEY = "e8657e8a-7345-4158-a933-9b9f07cacb1e"
DEVICE_ID = "6addbd02814fdde8893b2883"

def send_sinric_action(action, value_dict):
    url = f"https://api.sinric.pro/api/v1/devices/{DEVICE_ID}/action"
    payload = {
        "type": "request",
        "action": action,
        "value": str(value_dict) if not isinstance(value_dict, str) else value_dict
    }
    headers = {
        "X-SINRIC-API-KEY": SINRIC_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Sinric API Error: {e}")
        return False

@app.get("/")
def root():
    return {"status": "Bridge is running!"}

# 1. Запрос списка устройств от Яндекса (Discovery)
@app.get("/v1.0/user/devices")
@app.post("/v1.0/user/devices")
async def get_devices(request: Request):
    return {
        "request_id": request.headers.get("X-Request-Id", "123"),
        "payload": {
            "devices": [
                {
                    "id": DEVICE_ID,
                    "name": "Люстра",
                    "description": "BLE Люстра через ESP32 и Sinric Pro",
                    "room": "Спальня",
                    "type": "devices.types.light",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.on_off",
                            "retrievable": True
                        },
                        {
                            "type": "devices.capabilities.range",
                            "retrievable": True,
                            "parameters": {
                                "instance": "brightness",
                                "unit": "unit.percent",
                                "range": {"min": 0, "max": 100, "precision": 1}
                            }
                        },
                        {
                            "type": "devices.capabilities.color_setting",
                            "retrievable": True,
                            "parameters": {
                                "temperature_k": {
                                    "min": 2700,
                                    "max": 6000
                                }
                            }
                        }
                    ],
                    "device_info": {
                        "manufacturer": "Custom ESP32",
                        "model": "ChandelierBLE",
                        "hw_version": "1.0",
                        "sw_version": "3.5.2"
                    }
                }
            ]
        }
    }

# 2. Обработка команд управления от Яндекса (Action)
@app.post("/v1.0/user/devices/action")
async def device_action(request: Request):
    data = await request.json()
    req_id = request.headers.get("X-Request-Id", "123")
    
    results = []
    for dev in data.get("devices", []):
        dev_id = dev.get("id")
        dev_results = []
        
        for cap in dev.get("capabilities", []):
            cap_type = cap.get("type")
            state = cap.get("state", {})
            instance = state.get("instance")
            value = state.get("value")
            
            success = False
            if cap_type == "devices.capabilities.on_off":
                action = "setPowerState"
                val = "On" if value else "Off"
                success = send_sinric_action(action, {"state": val})
                
            elif cap_type == "devices.capabilities.range" and instance == "brightness":
                success = send_sinric_action("setBrightness", {"brightness": int(value)})
                
            elif cap_type == "devices.capabilities.color_setting" and instance == "temperature_k":
                success = send_sinric_action("setColorTemperature", {"colorTemperature": int(value)})
            
            if success:
                dev_results.append({
                    "achieved": {
                        "type": cap_type,
                        "state": {"instance": instance, "value": value} if instance else {"value": value}
                    },
                    "status": "DONE"
                })
            else:
                dev_results.append({"status": "ERROR"})
                
        results.append({"id": dev_id, "capabilities": dev_results})
        
    return {"request_id": req_id, "payload": {"devices": results}}

# 3. Запрос актуального состояния от Яндекса (Query)
@app.post("/v1.0/user/devices/query")
async def device_query(request: Request):
    data = await request.json()
    req_id = request.headers.get("X-Request-Id", "123")
    return {
        "request_id": req_id,
        "payload": {
            "devices": [
                {
                    "id": DEVICE_ID,
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}},
                        {"type": "devices.capabilities.range", "state": {"instance": "brightness", "value": 60}},
                        {"type": "devices.capabilities.color_setting", "state": {"instance": "temperature_k", "value": 4000}}
                    ]
                }
            ]
        }
    }
