#!/usr/bin/env python3

import hashlib
import base64
import requests
import paho.mqtt.client as mqtt
import os
import json
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
sid = config.get("sid", None)
uri = None
debug = config.get("debug", "false").lower() == "true"  # Check if debug is enabled in config

# Load request interval with validation
request_interval_seconds = 60  # Default value
try:
    request_interval_seconds = int(config.get("request_interval_seconds", request_interval_seconds))
except ValueError:
    print(f"Invalid value for 'request_interval_seconds' in config, defaulting to {request_interval_seconds} seconds.")

def save_token_to_config(token):
    config["token"] = token
    save_config(config_file, config)

def save_sid_to_config(sid):
    config["sid"] = sid
    save_config(config_file, config)

# def save_uri_to_config(uri):
#     config["uri"] = uri
#     save_config(config_file, config)

# Function to print debug messages (if debug is enabled)
def debug_print(message):
    if debug:
        print(message)

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

        # Step 3: Send the first web request with the generated string
        url_login = "https://euapi.hoymiles.com/iam/pub/0/c/login_c"
        headers = {'Content-Type': 'application/json; charset=utf-8'}

        data_login = {
            "user_name": hoymiles_user,
            "password": encoded_password
        }

        # Send the POST request for login
        response_login = requests.post(url_login, json=data_login, headers=headers)

        # Check the response
        if response_login.status_code == 200:
            try:
                response_data = response_login.json()
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

        data_station = {
            "page": 1,
            "page_size": 50
        }

        response_station = requests.post(url_station, json=data_station, headers=headers_with_auth)

        if response_station.status_code == 200:
            try:
                station_data = response_station.json()
                debug_print(f"Station Data Response: {station_data}")

                if station_data.get("status") == "0":
                    # Use JSONPath to extract the 'sid'
                    jsonpath_expr = parse('$.data.list[0].sid')
                    match = jsonpath_expr.find(station_data)

                    if match:
                        localsid = match[0].value
                        debug_print(f"SID retrieved: {localsid}")
                        save_sid_to_config(localsid)
                        return localsid
                    else:
                        debug_print("SID not found in station data response.")
                        return None
                else:
                    debug_print(f"Failed to retrieve station data: {station_data.get('message')}")
                    return None
            except ValueError as e:
                debug_print(f"Error decoding JSON response: {e}")
                return None
        else:
            debug_print(f"Failed to fetch station data. Status Code: {response_station.status_code}")
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
                sd_uri_data = response_sd_uri.json()
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

    # Step 6: Use the token and uri to send the fourth request

    final_data = {
        "m": 0,
        "sid": flowsid
    }

    response_final = requests.post(flowuri, json=final_data, headers={'Authorization': flowtoken})

    if response_final.status_code == 200:
        final_data_response = response_final.json()
        debug_print(f"Final Data Response: {final_data_response}")

        # Use JSONPath to extract values
        status_expr = parse('$.status')
        dly_expr = parse('$.data.dly')
        soc_expr = parse('$.data.soc')
        first_flow_expr = parse('$.data.flow[0]')  # Extract only the first block of $.data.flow

        # Extract status
        status = [match.value for match in status_expr.find(final_data_response)]
        if status and status[0] == "0":
            # Extract delay
            dly = [match.value for match in dly_expr.find(final_data_response)]
            if dly and dly[0] == 10000:
                debug_print("Received response with dly: 10000, requesting a new URI.")
                global request_interval_seconds
                if request_interval_seconds < (dly[0]/1000):
                    request_interval_seconds = (dly[0]/1000)
                    debug_print(f"new request_interval_seconds: {request_interval_seconds}")
                else:
                    request_interval_seconds = 15
                global uri
                uri = None
            else: 

                # Extract SOC
                soc = [match.value for match in soc_expr.find(final_data_response)]
                soc = soc[0] if soc else None

                # Extract the first block of flow data
                first_flow = [match.value for match in first_flow_expr.find(final_data_response)]
                first_flow = first_flow[0] if first_flow else None

                if soc is not None and first_flow:
                    # Publish data to MQTT broker
                    client = mqtt.Client()
                    client.username_pw_set(mqtt_user, mqtt_password)

                    client.connect(mqtt_broker, 1883, 60)
                    client.publish(mqtt_topic, json.dumps(final_data_response))

                    i = first_flow.get("i")
                    o = first_flow.get("o")
                    v = first_flow.get("v")
                    debug_print(f"i: {i} o: {o} v: {v}")

                    power_battery_topic = "hoymiles-ms-a2/power-battery"
                    
                    battery_power = 0
                    if i == 20 and o == 40 and v is not None:
                        battery_power = v
                    elif i == 40 and o == 20 and v is not None:
                        battery_power = -v
                    client.publish(power_battery_topic, battery_power)

                    print(
                        f"SOC retrieved: {soc}  | power-battery: {battery_power} "
                    )

                    client.disconnect()
                else:
                    debug_print("SOC not found.")
        else:
            debug_print(f"Failed to retrieve final data: {final_data_response.get('message')}")
    else:
        debug_print(f"Failed to fetch final data. Status Code: {response_final.status_code}")

# Main logic

try:
    while True:
        # Log the start timestamp
        debug_print(f"running at: {datetime.now().isoformat()}")

        if not token:
            debug_print("No token found. Requesting a new one.")
            token = request_new_token()
        else: 
            if not sid:
                debug_print("No sid found. Requesting a new one.")
                sid = get_sid (token)
            else:
                debug_print("SID loaded from config.")

        if token and sid:
            if not uri:
                debug_print("No uri found. Requesting a new one.")
                uri = get_uri(token, sid)
            if uri:
                debug_print("using cached uri.")
                get_flow_data(token, sid, uri)
            else:
                debug_print("no uri, no final request!")

        time.sleep(request_interval_seconds)

except KeyboardInterrupt:
    debug_print("\nScript terminated by user (Ctrl+C). Exiting gracefully.")











