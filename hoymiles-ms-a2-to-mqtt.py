#!/usr/bin/env python3

import hashlib
import base64
import requests
import paho.mqtt.client as mqtt
import os
import json5
import time
from datetime import datetime
from jsonpath_ng import parse

# Function to load configuration variables from a file
def load_config(config_file):
    config = {}
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            for line in file:
                key, value = line.strip().split("=", 1)
                config[key.strip()] = value.strip()
    return config

# Function to save configuration variables to a file
def save_config(config_file, config):
    with open(config_file, "w") as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")

# Load configuration variables
config_file = os.path.join(os.path.dirname(__file__), "hoymiles-ms-a2-to-mqtt.config")
config = load_config(config_file)

hoymiles_user = config.get("hoymiles_user", "")
hoymiles_password = config.get("hoymiles_password", "")
mqtt_broker = config.get("mqtt_broker", "")
mqtt_user = config.get("mqtt_user", "")
mqtt_password = config.get("mqtt_password", "")
mqtt_topic = config.get("mqtt_topic", "")
token = config.get("token", None)
login_url = config.get("login_url", None)
sid = config.get("sid", None)
inverterId = config.get("inverterId", None)
uri = None
debug = config.get("debug", "false").lower() == "true"  # Check if debug is enabled in config

# Function to print debug messages (if debug is enabled)
def debug_print(message):
    if debug:
        #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        #print(f"[{timestamp}] {message}")
        print(f"{message}")


# Initialize last station data fetch time
last_station_data_time = 0


# Load request interval with validation
request_interval_seconds = 60  # Default value
try:
    request_interval_seconds = int(config.get("request_interval_seconds", request_interval_seconds))
    debug_print(f"Request Interval in Seconds: {request_interval_seconds}")
except ValueError:
    debug_print(f"Invalid value for 'request_interval_seconds' in config, defaulting to {request_interval_seconds} seconds.")

# Load station interval with validation
station_data_interval = 3600  # 1 hour in seconds
try:
    station_data_interval = int(config.get("station_data_interval", station_data_interval))
    debug_print(f"Station Data Interval in Seconds: {station_data_interval}")
except ValueError:
    debug_print(f"Invalid value for 'station_data_interval' in config, defaulting to {station_data_interval} seconds.")


# Load port with validation
mqtt_port = 1883  # Default value
try:
    mqtt_port = int(config.get("mqtt_port", mqtt_port))
except ValueError:
    debug_print(f"Invalid value for 'mqtt_port' in config, defaulting to {mqtt_port} seconds.")


def save_login_url_to_config(login_url):
    config["login_url"] = login_url
    save_config(config_file, config)

def save_token_to_config(token):
    config["token"] = token
    save_config(config_file, config)

def save_sid_to_config(sid):
    config["sid"] = sid
    save_config(config_file, config)

def save_inverterId_to_config(sid):
    config["inverterId"] = inverterId
    save_config(config_file, config)

# def save_uri_to_config(uri):
#     config["uri"] = uri
#     save_config(config_file, config)

# Initialize MQTT client once
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(mqtt_user, mqtt_password)
mqtt_client.connect(mqtt_broker, mqtt_port, 60)

def publish_mqtt(topic, payload, publishAsRetain=False):
    """
    Publishes data to the MQTT broker.
    :param topic: MQTT topic
    :param payload: Data to publish (dict or primitive type)
    """
    try:
        mqtt_client.publish(topic, payload, publishAsRetain)
        # debug_print(f"Published to {topic}: {payload}")
    except Exception as e:
        debug_print(f"MQTT error: {e}")


# Function to request a new token
def request_new_token():
    try:
        # Step 1: Generate the MD5 hash
        md5_hash = hashlib.md5(hoymiles_password.encode('utf-8')).hexdigest()

        # Step 2: Generate the SHA-256 hash and encode it in Base64
        sha256_hash = hashlib.sha256(hoymiles_password.encode('utf-8')).digest()
        base64_hash = base64.b64encode(sha256_hash).decode('utf-8')

        # Combine the two parts to form the final string
        encoded_password = f"{md5_hash}.{base64_hash}"

        # get region for login

        url_region = "https://euapi.hoymiles.com/iam/pub/0/c/region_c"
        payload_region = { "email": hoymiles_user }
        headers = {'Content-Type': 'application/json; charset=utf-8'}

        response_region = requests.post(url_region, json=payload_region, headers=headers)

        if response_region.status_code == 200:
            try:
                response_region_data = json5.loads(response_region.text)
                if response_region_data.get("status") == "0" and "data" in response_region_data:
                    debug_print(f"Region Data Response: {response_region_data}")
                    login_url = response_region_data["data"].get("login_url")
                    if login_url:
                        save_login_url_to_config(login_url)
                else:
                    debug_print(f"Error Message: {response_region_data.get('message')}")
                    token = None
            except ValueError as e:
                debug_print(f"Error decoding JSON response: {e}")
                token = None
        else:
            debug_print(f"Failed to get region. Status Code: {response_region.status_code}")
            token = None


        # Step 3: Send the first web request with the generated string
        #get_token_url = "https://euapi.hoymiles.com/iam/pub/0/c/login_c"
        get_token_url = login_url + "/iam/pub/0/c/login_c"


        data_login = {
            "user_name": hoymiles_user,
            "password": encoded_password
        }

        # Send the POST request for login
        response_login = requests.post(get_token_url, json=data_login, headers=headers)

        # Check the response
        if response_login.status_code == 200:
            try:
                response_data = json5.loads(response_login.text)
                if response_data.get("status") == "0" and "data" in response_data:
                    debug_print(f"Token Data Response: {response_data}")
                    token = response_data["data"].get("token")
                    if token:
                        save_token_to_config(token)
                else:
                    debug_print(f"Error Message: {response_data.get('message')}")
                    token = None
            except ValueError as e:
                debug_print(f"Error decoding JSON response: {e}")
                token = None
        else:
            debug_print(f"Failed to login. Status Code: {response_login.status_code}")
            token = None

    except requests.RequestException as e:
        debug_print(f"Request failed: {e}")
        token = None

    except Exception as e:
        debug_print(f"An unexpected error occurred: {e}")
        token = None

    return token

def get_sid(localtoken):
    try:
        # Use the token to send a request for the SID
        url_station = "https://neapi.hoymiles.com/pvmc/api/0/station/select_by_page_c"
        headers_with_auth = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': localtoken
        }
        data_station = {"page": 1, "page_size": 50}
        response_station = requests.post(url_station, json=data_station, headers=headers_with_auth)

        if response_station.status_code == 200:
            try:
                station_data = json5.loads(response_station.text)
                debug_print(f"Get Sid Response: {station_data}")

                if station_data.get("status") == "0":
                    # Use JSONPath to extract the 'sid'
                    jsonpath_sid = parse('$.data.list[0].sid')
                    match_sid = jsonpath_sid.find(station_data)

                    jsonpath_devices = parse("$..devices[*]")
                    devices = [match.value for match in jsonpath_devices.find(station_data)]
                    
                    global inverterId
                    for device in devices:
                        if device.get("type") == 6:
                            inverterId = device.get("id")
                            break
                    
                    if inverterId:
                        debug_print(f"ID with type 6 retrieved: {inverterId}")
                        save_inverterId_to_config(inverterId)
                    else:
                        debug_print("ID with type 6 not found in get sid response.")

                    if match_sid:
                        localsid = match_sid[0].value
                        debug_print(f"SID retrieved: {localsid}")
                        save_sid_to_config(localsid)
                        return localsid
                    else:
                        debug_print("SID not found in get sid response.")
                        return None
                else:
                    debug_print(f"Failed to retrieve sid data: {station_data.get('message')}")
                    return None
            except ValueError as e:
                debug_print(f"Error decoding JSON response: {e}")
                return None
        else:
            debug_print(f"Failed to fetch sid data. Status Code: {response_station.status_code}")
            return None

    except requests.RequestException as e:
        debug_print(f"Request failed: {e}")
        return None
    except Exception as e:
        debug_print(f"An unexpected error occurred: {e}")
        return None

def get_uri(localtoken, localsid):
    try:
        # Step 5: Use the token and sid to get the uri
        url_sd_uri = "https://neapi.hoymiles.com/pvmc/api/0/station/get_sd_uri_c"
        headers_with_auth = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': localtoken
        }

        data_sd_uri = {"sid": localsid}

        response_sd_uri = requests.post(url_sd_uri, json=data_sd_uri, headers=headers_with_auth)

        if response_sd_uri.status_code == 200:
            try:
                sd_uri_data = json5.loads(response_sd_uri.text)
                debug_print(f"SD URI Data Response: {sd_uri_data}")

                if sd_uri_data.get("status") == "0" and "data" in sd_uri_data:
                    localuri = sd_uri_data["data"].get("uri")
                    if localuri:
                        debug_print(f"URI retrieved: {localuri}")
                        return localuri
                    else:
                        debug_print("URI not found in sd_uri data response.")
                        return None
                else:
                    debug_print(f"Failed to retrieve sd_uri data: {sd_uri_data.get('message')}")
                    global token
                    token = None
                    debug_print("requesting new token...")
                    return None
            except ValueError as e:
                debug_print(f"Error decoding JSON response: {e}")
                return None
        else:
            debug_print(f"Failed to fetch sd_uri. Status Code: {response_sd_uri.status_code}")
            if response_sd_uri.status_code == 400:  # Bad Request, trigger re-request of URI
                return None
            return None

    except requests.RequestException as e:
        debug_print(f"Request failed: {e}")
        return None

    except Exception as e:
        debug_print(f"An unexpected error occurred: {e}")
        return None

# Function to handle the final request logic
def get_flow_data(flowtoken, flowsid, flowuri):
    try:
        final_data = {"m": 0, "sid": flowsid}
        headers = {'Authorization': flowtoken}

        try:
            response_final = requests.post(flowuri, json=final_data, headers=headers, timeout=10)
            response_final.raise_for_status()  # Raise an error for 4xx/5xx responses
        except requests.exceptions.RequestException as e:
            debug_print(f"Request failed: {e}")
            return

        try:
            final_data_response = json5.loads(response_final.text)
        except (json5.JSONDecodeError, ValueError) as e:
            debug_print(f"JSON decoding error: {e}")
            return

        debug_print(f"Final Data Response: {final_data_response}")

        status_expr = parse('$.status')
        dly_expr = parse('$.data.dly')
        soc_expr = parse('$.data.soc')
        first_flow_expr = parse('$.data.flow[0]')

        status = [match.value for match in status_expr.find(final_data_response)]
        if not status or status[0] != "0":
            debug_print(f"Failed to retrieve final data: {final_data_response.get('message', 'Unknown error')}")
            return

        dly = [match.value for match in dly_expr.find(final_data_response)]
        if dly and dly[0] == 10000:
            debug_print("Received response with dly: 10000, requesting a new URI.")
            #global request_interval_seconds
            #request_interval_seconds = max(15, dly[0] / 1000)
            #debug_print(f"new request_interval_seconds: {request_interval_seconds}")
            global uri
            uri = None
            return

        soc = [match.value for match in soc_expr.find(final_data_response)]
        soc = soc[0] if soc else None

        first_flow = [match.value for match in first_flow_expr.find(final_data_response)]
        first_flow = first_flow[0] if first_flow else None

        if soc is None or not first_flow:
            debug_print("SOC or flow data not found.")
            return

        mqtt_topic_flow = mqtt_topic + "/flow"
        publish_mqtt(mqtt_topic_flow, json5.dumps(final_data_response))

        i = first_flow.get("i")
        o = first_flow.get("o")
        v = first_flow.get("v")

        debug_print(f"i: {i} o: {o} v: {v}")

        power_battery_topic = mqtt_topic + "/power-battery"
        soc_topic =  mqtt_topic + "/soc"
        publish_mqtt(soc_topic, soc)

        battery_power = 0
        if i == 20 and o == 40 and v is not None:
            battery_power = v
        elif i == 40 and o == 20 and v is not None:
            battery_power = -v

        publish_mqtt(power_battery_topic, battery_power)
        debug_print(f"SOC retrieved: {soc}  | power-battery: {battery_power}")

    except Exception as e:
        debug_print(f"Unexpected error: {e}")


# Function to handle the final request logic
def get_station_data(stationtoken, stationsid):
    try:
        station_data = {"sid": stationsid}
        headers = {'Authorization': stationtoken}
        station_url = "https://eud0.hoymiles.com/pvmc/api/0/station_data/real_g_c"

        try:
            response_station = requests.post(station_url, json=station_data, headers=headers, timeout=10)
            response_station.raise_for_status()  # Raise an error for 4xx/5xx responses
        except requests.exceptions.RequestException as e:
            debug_print(f"Request failed: {e}")
            return

        try:
            station_data_response = json5.loads(response_station.text)
        except (json5.JSONDecodeError, ValueError) as e:
            debug_print(f"JSON decoding error: {e}")
            return

        debug_print(f"Station Data Response: {station_data_response}")

        status_expr = parse('$.status')
        bms_in_eq_expr = parse('$.data.reflux_station_data.bms_in_eq')
        bms_out_eq_expr = parse('$.data.reflux_station_data.bms_out_eq')


        status = [match.value for match in status_expr.find(station_data_response)]
        if not status or status[0] != "0":
            debug_print(f"Failed to retrieve station data: {station_data_response.get('message', 'Unknown error')}")
            return

        bms_in_eq = [match.value for match in bms_in_eq_expr.find(station_data_response)]
        bms_in_eq = bms_in_eq[0] if bms_in_eq else None

        bms_out_eq = [match.value for match in bms_out_eq_expr.find(station_data_response)]
        bms_out_eq = bms_out_eq[0] if bms_out_eq else None

        mqtt_topic_station = mqtt_topic + "/station"
        publish_mqtt(mqtt_topic_station, json5.dumps(station_data_response))

        debug_print(f"bms_in_eq retrieved: {bms_in_eq}  | bms_out_eq: {bms_out_eq}")

    except Exception as e:
        debug_print(f"Unexpected error: {e}")


# Function to handle the final request logic
def get_inverter_data(inverterToken, inverterSid, inverterId):
    try:
        inverter_data = {"id": inverterId,"sid": inverterSid}
        headers = {'Authorization': inverterToken}
        inverter_url = "https://neapi.hoymiles.com/pvmc/api/0/inverter/find_c"

        try:
            inverter_response = requests.post(inverter_url, json=inverter_data, headers=headers, timeout=10)
            inverter_response.raise_for_status()  # Raise an error for 4xx/5xx responses
        except requests.exceptions.RequestException as e:
            debug_print(f"Request failed: {e}")
            return

        try:
            inverter_data_response = json5.loads(inverter_response.text)
        except (json5.JSONDecodeError, ValueError) as e:
            debug_print(f"JSON decoding error: {e}")
            return

        debug_print(f"Inverter Data Response: {inverter_data_response}")

        status_expr = parse('$.status')
        bms_temp_expr = parse('$.data.real_data.bms_temp')


        status = [match.value for match in status_expr.find(inverter_data_response)]
        if not status or status[0] != "0":
            debug_print(f"Failed to retrieve inverter data: {inverter_data_response.get('message', 'Unknown error')}")
            return

        bms_temp = [match.value for match in bms_temp_expr.find(inverter_data_response)]
        bms_temp = bms_temp[0] if bms_temp else None

        mqtt_topic_station = mqtt_topic + "/inverter"
        publish_mqtt(mqtt_topic_station, json5.dumps(inverter_data_response))
        debug_print(f"bms_temp retrieved: {bms_temp}")


    except Exception as e:
        debug_print(f"Unexpected error: {e}")


def exponential_backoff(attempt):
    return min(60, (2 ** attempt))

# Main logic
try:
    token_request_attempts = 0
    while True:
        current_time = time.time()
        
        if not token:
            debug_print("No token found. Requesting a new one.")
            token = request_new_token()
            if not token:
                time.sleep(exponential_backoff(token_request_attempts))
                token_request_attempts += 1
            else:
                token_request_attempts = 0

        if token and not sid:
            debug_print("No sid found. Requesting a new one.")
            sid = get_sid(token)
        
        if token and sid:
            if not uri:
                debug_print("No uri found. Requesting a new one.")
                uri = get_uri(token, sid)
            if uri:
                debug_print("Using cached uri.")
                get_flow_data(token, sid, uri)
                
                # Call get_station_data every 1 hour
                if current_time - last_station_data_time >= station_data_interval:
                    get_station_data(token, sid)
                    if inverterId:
                        get_inverter_data(token, sid, inverterId)
                    else:
                        debug_print("no inverterID")
                    last_station_data_time = current_time
            else:
                debug_print("No uri, no final request!")

        time.sleep(request_interval_seconds)

except KeyboardInterrupt:
    debug_print("\nScript terminated by user (Ctrl+C). Exiting gracefully.")
    mqtt_client.disconnect()
