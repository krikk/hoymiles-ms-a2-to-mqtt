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
  - ```{'status': '0', 'data': {'flow': [{'i': 40, 'o': 20, 'v': 245.8}, {'i': 1, 'o': 40, 'v': 252.0}, {'i': 40, 'o': 2, 'v': 6.2}, {'i': 20, 'o': 10, 'v': 245.8}], 'dly': 3000, 'con': 1, 'soc': 53.0, 'power': {'pv': 0.0, 'bat': 245.8, 'grid': 6.2, 'load': 252.0, 'sp': 0.0}, 'brs': 2, 'bhs': 0, 'ems': 0}}```
  - soc it the State of Charge of the battery, grid and load a current power values, flow gives load to/from battery

## TODO
- get more data
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
chmod a+x hoymiles-ms-a2-to-mqtt.py
```


* modify your configuration (hoymiles-ms-a2-to-mqtt.config) and test it
```
./hoymiles-ms-a2-to-mqtt.py
```

#### Install as systemd service (untested)
Debian
```
cp /opt/hoymiles-ms-a2-to-mqtt/hoymiles-ms-a2-to-mqtt.service /etc/systemd/system
```


```
systemctl daemon-reload
systemctl start hoymiles-ms-a2-to-mqtt
systemctl enable hoymiles-ms-a2-to-mqtt
```
## How to Sniff the App Traffic

i used an android studio emulator with android 12... 

then followed basically this guide: https://emanuele-f.github.io/PCAPdroid/tls_decryption#34-caveats-and-possible-solutions 

1. add adb to path, to make the rootAVD script work
2. ...used https://gitlab.com/newbit/rootAVD to root the emulator and install magisk
3. in magisk i installed this module: https://github.com/NVISOsecurity/MagiskTrustUserCerts <- this adds user imported certs to system trust store... (same for newer android: https://github.com/pwnlogs/cert-fixer) 
4. install PCAPdroid and install CA Certificate
5. rebootet emulator (the magisk module only copies user the certificate to system store on boot)

and afterwards TLS decryption with PCAPdroid works...
