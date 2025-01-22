# hoymiles-ms-a2-to-mqtt
Python Script to get Data from Hoymiles Cloud for the Hoymiles MS A2 Battery System to MQTT Broker

## Features
- Login to Hoymiles Cloud to get Token and cache it
- with the Token get the sid and cache it
- with  the token and the sid get the uri and cache it
- with the Token and the uri we can get the JSON data (which will be directly published to mqtt) with the SOC and power values, as long as the uri is valid

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
