# hoymiles-ms-a2-to-mqtt
Python Script to get Data from Hoymiles Cloud for the Hoymiles MS A2 Battery System to MQTT Broker

## Features
- Login to Hoymiles Cloud to get Token and cache it, sample response:
  - ```{'status': '0', 'message': 'success', 'data': {'token': '2.xxxxxxxxxxxxxxxxxxxxxxx.1'}}```
- with the Token get the sid and cache it, sample response:
  - ```{'status': '0', 'message': 'success', 'data': {'page': 1, 'page_size': 50, 'total': 1, 'list': [{'sid': xxxx, 'sn': 'xxxx', 'name': 'xxxx-home', 'area_code': 'AT', 'classify': 10, 'devices': [{'id': 75460, 'sn': 'xxx', 'dtu_sn': 'xx', 'type': 1, 'warn_data': {'connect': True, 'warn': False}, 'extend_data': {'dfs': xx, 'inner': 1}, 'devices': [{'id': xx, 'sn': 'xx', 'dtu_sn': 'xx', 'type': 6, 'warn_data': {'connect': True, 'warn': False}, 'extend_data': {'role': 0}, 'devices': [{'id': xx, 'sn': 'xx', 'dtu_sn': 'xx', 'type': 16, 'warn_data': {'connect': True}, 'extend_data': {'name': 'ShellyPro3EM', 'type': 2, 'model': 'xxx'}, 'devices': []}]}]}], 'dc': 1, 'ak': 'xxxx', 'bt': 1}]}}```
- with  the token and the sid get the uri and cache it, sample response:
  - ```{'status': '0', 'message': 'success', 'data': {'uri': 'https://eurt.hoymiles.com/rds/api/0/burst/get?k=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&t=<UNIXTIMESTAMP>'}}```
- with the Token and the uri we can get the JSON data (which will be directly published to mqtt) with the SOC and power values, as long as the uri is valid, sample response:
  - ```{"status": "0", "data": {"flow": [{"i": 1, "o": 40, "v": 224.4}, {"i": 40, "o": 2, "v": 224.4}], "dly": 3000, "con": 1, "soc": 10.0, "power": {"pv": 0.0, "bat": 0.0, "grid": 224.4, "load": 224.4, "sp": 0.0}, "brs": 0, "bhs": 0, "ems": 0}}```
  - soc it the State of Charge of the battery, grid and load a current power values, flow gives load to/from battery

## TODO
- mostly chatGPT generated code...
- better error handling
- get rest of config paramters
- set config parameters

## Installation

### Debian

```shell
sudo apt-get install python3-virtualenv
cd /opt
git clone https://github.com/krikk/hoymiles-ms-a2-to-mqtt.git
cd hoymiles-ms-a2-to-mqtt
virtualenv -p python3 .venv
. .venv/bin/activate
pip3 install -r requirements.txt
```


* modify your configuration (hoymiles-ms-a2-to-mqtt.config) and test it
```
./hoymiles-ms-a2-to-mqtt.py
```
