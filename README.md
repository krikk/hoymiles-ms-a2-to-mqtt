# hoymiles-ms-a2-to-mqtt
Python Script to get Data from Hoymiles Cloud for the Hoymiles MS A2 Battery System to MQTT Broker

## Features
get the following data out from Hoymiles Clout and publish it to the MQTT Broker:
- soc: State of Charge (to make i easier accessible, because SOC is also in the "raw" flow data)
- power-battery:
  - positive value: how much power (in Watt) is going to Battery
  - negative value: how much power (in Watt) is discharged from Battery
- flow: raw flow data, like we get it from the api
  - Sample: ```{'status': '0', 'data': {'flow': [{'i': 40, 'o': 20, 'v': 245.8}, {'i': 1, 'o': 40, 'v': 252.0}, {'i': 40, 'o': 2, 'v': 6.2}, {'i': 20, 'o': 10, 'v': 245.8}], 'dly': 3000, 'con': 1, 'soc': 53.0, 'power': {'pv': 0.0, 'bat': 245.8, 'grid': 6.2, 'load': 252.0, 'sp': 0.0}, 'brs': 2, 'bhs': 0, 'ems': 0}}```
- station: raw station data, like we get it from the api (this contains today charge and discharge values)
  - Sample: ```{'status': '0', 'message': 'success', 'data': {'is_null': 0, 'today_eq': '1', 'month_eq': '20', 'year_eq': '104', 'total_eq': '125', 'real_power': '0', 'co2_emission_reduction': '124.625', 'plant_tree': '0', 'data_time': '2025-02-06 15:12:30', 'last_data_time': '2025-02-06 15:12:30', 'capacitor': '2', 'is_balance': 0, 'is_reflux': 1, 'reflux_station_data': {'start_date': '2025-02-06', 'end_date': '2025-02-06', 'pv_power': '0', 'grid_power': '0', 'load_power': '0', 'bms_power': '0', 'bms_soc': '10.0', 'inv_num': 1, 'meter_location': 2, 'pv_to_load_eq': '177', 'load_from_pv_eq': '177', 'meter_b_in_eq': '1159', 'meter_b_out_eq': '2', 'bms_in_eq': '285', 'bms_out_eq': '641', 'self_eq': '0', 'pv_eq_total': '0', 'use_eq_total': '0', 'flows': [], 'icon_pv': 0, 'icon_grid': 1, 'icon_load': 1, 'icon_bms': 1, 'icon_gen': 0, 'icon_pvi': 0, 'mb_in_eq': {'today_eq': '0', 'month_eq': '0', 'year_eq': '0', 'total_eq': '0'}, 'mb_out_eq': {'today_eq': '2', 'month_eq': '0', 'year_eq': '0', 'total_eq': '0'}, 'icon_plug': 0, 'icon_ai_plug': 0, 'cfg_load_power': 0}, 'clp': 0, 'efl_today_eq': None, 'efl_month_eq': None, 'efl_year_eq': None, 'efl_total_eq': None, 'electricity_price': 0.0, 'unit_code': '', 'unit': None, 'tou_mode': 2, 'is_load':0, 'warn_data': None}}```
- raw inverter data, like we get it from the api (this contains bms_temp)
  - Sample: ```{'status': '0', 'message': 'success', 'data': {'id': 3423, 'sn': 'xxx', 'dtu_id': xxx, 'dtu_sn': 'xxx', 'dev_type': None, 'role': 0, 'create_by': 324344, 'create_at': '2024-12-19 20:20:03', 'update_by': 3424, 'update_at': '2024-12-19 20:20:03', 'soft_ver': None, 'hard_ver': None, 'dsp_sw': 10304, 'wifi_sw': 4870, 'bms_sw': 16846080, 'warn_data': {'connect': True, 'warn': False}, 'real_data': {'bms_soc': '10.0', 'bms_temp': '22.0', 'bms_state': 0}}}```
- basic Home Assistant MQTT Autodiscovery (only for power/to/from battery and SoC)

## TODO
- Full Home Assistant Autodiscovery
- get rest of config paramters
- set config parameters (e.g. Force Load)

## Installation

### docker-compose


docker-compose.yml
```yml
version: "3"
services:
  hoymiles-cloud-mqtt:
    image: badsmoke/hoymiles-ms-a2-mqtt    
    restart: always
    environment:
      - HOYMILES_USER=hoymiles-user@email.com
      - HOYMILES_PASSWORD=HoymilesPassword
      - MQTT_BROKER=192.168.1.23
      - MQTT_USER=mqtt-user
      - MQTT_PASSWORD=mqtt-password
      - MQTT_TOPIC=hoymiles-ms-a2
      - MQTT_PORT=1883
      - REQUEST_INTERVAL_SECONDS=15
      - STATION_DATA_INTERVAL=3600
      - DEBUG=true
```
`sudo docker compose up -d`

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

#### Install as systemd service
Debian

User=USERNAME in hoymiles-ms-a2-to-mqtt.service has to be changed.

```
cp /opt/hoymiles-ms-a2-to-mqtt/hoymiles-ms-a2-to-mqtt.service /etc/systemd/system
```


```
systemctl daemon-reload
systemctl start hoymiles-ms-a2-to-mqtt
systemctl enable hoymiles-ms-a2-to-mqtt
```

### How to get full debug logs:
- stop the script
- open the .config file and remove the lines with sid, token, id (everything except the needed login info)
- start the script

## Hoymiles API
use this basic [Bruno](https://www.usebruno.com/) [Collection](https://github.com/krikk/hoymiles-ms-a2-to-mqtt/tree/main/hoymiles-api) to test the hoymiles api


## How to Sniff the App Traffic

i used an android studio emulator with android 12... 

then followed basically this guide: https://emanuele-f.github.io/PCAPdroid/tls_decryption#34-caveats-and-possible-solutions 

1. add adb to path, to make the rootAVD script work
2. ...used https://gitlab.com/newbit/rootAVD to root the emulator and install magisk
3. in magisk i installed this module: https://github.com/NVISOsecurity/MagiskTrustUserCerts <- this adds user imported certs to system trust store... (same for newer android: https://github.com/pwnlogs/cert-fixer) 
4. install PCAPdroid and install CA Certificate
5. rebootet emulator (the magisk module only copies user the certificate to system store on boot)

and afterwards TLS decryption with PCAPdroid works...
