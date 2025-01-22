#!/usr/bin/env python3

import hashlib
import base64
import requests
import paho.mqtt.client as mqtt
import os
import json
import time
from datetime import datetime



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
uri = config.get("uri", None)  # Load uri from config if available
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

def save_uri_to_config(uri):
    config["uri"] = uri
    save_config(config_file, config)

# Function to print debug messages (if debug is enabled)
def debug_print(message):
    if debug:
        print(message)

# Function to request a new token
def request_new_token():
    # Step 1: Generate the MD5 hash
    md5_hash = hashlib.md5(hoymiles_password.encode('utf-8')).hexdigest()

    # Step 2: Generate the SHA-256 hash and encode it in Base64
    sha256_hash = hashlib.sha256(hoymiles_password.encode('utf-8')).digest()
    base64_hash = base64.b64encode(sha256_hash).decode('utf-8')

    # Combine the two parts to form the final string
    final_string = f"{md5_hash}.{base64_hash}"

    # Step 3: Send the first web request with the generated string
    url_login = "https://euapi.hoymiles.com/iam/pub/0/c/login_c"
    headers = {'Content-Type': 'application/json; charset=utf-8'}

    data_login = {
        "user_name": hoymiles_user,
        "password": final_string
    }

    # Send the POST request for login
    response_login = requests.post(url_login, json=data_login, headers=headers)

    if response_login.status_code == 200:
        response_data = response_login.json()
        if response_data.get("status") == "0" and "data" in response_data:
            debug_print(f"Token Data Response: {response_data}")
            token = response_data["data"].get("token")
            if token:
                save_token_to_config(token)
                return token
        else:
            debug_print(f"Login failed: {response_data.get('message')}")
    else:
        debug_print(f"Failed to login. Status Code: {response_login.status_code}")

    return None

# Function to handle the final request logic
def send_final_request():
    global token, sid, uri

    if token and sid:
        if not uri:  # Only request URI if it is not available in the config
            # Step 5: Use the token and sid to send the third request
            url_sd_uri = "https://neapi.hoymiles.com/pvmc/api/0/station/get_sd_uri_c"
            headers_with_auth = {
                'Content-Type': 'application/json; charset=utf-8',
                'Authorization': token
            }

            data_sd_uri = {"sid": sid}

            response_sd_uri = requests.post(url_sd_uri, json=data_sd_uri, headers=headers_with_auth)

            if response_sd_uri.status_code == 200:
                sd_uri_data = response_sd_uri.json()
                debug_print(f"SD URI Data Response: {sd_uri_data}")

                if sd_uri_data.get("status") == "0" and "data" in sd_uri_data:
                    uri = sd_uri_data["data"].get("uri")
                    if uri:
                        debug_print(f"URI retrieved: {uri}")
                        save_uri_to_config(uri)  # Save the URI to the config file
                else:
                    debug_print(f"Failed to retrieve sd_uri data: {sd_uri_data.get('message')}")
            else:
                debug_print(f"Failed to fetch sd_uri. Status Code: {response_sd_uri.status_code}")
                if response_sd_uri.status_code == 400:  # Bad Request, trigger re-request of URI
                    uri = None  # Reset URI so it gets requested again
        else:
            debug_print(f"Using cached URI: {uri}")

        # Step 6: Use the token and uri to send the fourth request
        if uri:
            final_data = {
                "m": 0,
                "sid": sid
            }

            response_final = requests.post(uri, json=final_data, headers={'Authorization': token})

            if response_final.status_code == 200:
                final_data_response = response_final.json()
                final_data_response_str = str(final_data_response).replace("'", '"')
                debug_print(f"Final Data Response: {final_data_response_str}")

                if final_data_response.get("status") == "0" and "data" in final_data_response:
                    # Check if the response contains {"status": "0", "data": {"dly": 10000}}
                    if final_data_response["data"].get("dly") == 10000:
                        debug_print("Received response with dly: 10000, requesting a new URI.")
                        uri = None  # Reset URI so it gets requested again

                    soc = final_data_response["data"].get("soc")
                    power_grid = final_data_response["data"].get("soc")
                    if soc is not None:
                        # Publish data to MQTT broker
                        client = mqtt.Client()
                        client.username_pw_set(mqtt_user, mqtt_password)

                        client.connect(mqtt_broker, 1883, 60)
                        client.publish(mqtt_topic, final_data_response_str)

                        # Extract additional values and publish if conditions are met
                        json_data = json.loads(final_data_response_str)
                        flow = json_data.get("data", {}).get("flow", [])
                        if flow:
                            i = flow[0].get("i")
                            o = flow[0].get("o")
                            v = flow[0].get("v")
                            power_to_battery_topic = "hoymiles-ms-a2/power-to-battery"
                            power_from_battery_topic = "hoymiles-ms-a2/power-from-battery"
                            power_battery_topic = "hoymiles-ms-a2/power-battery"


                            if i == 20 and o == 40 and v is not None:
                                client.publish(power_to_battery_topic, v)
                                client.publish(power_battery_topic, v)
                            else:
                                client.publish(power_to_battery_topic, 0)

                            if i == 40 and o == 20 and v is not None:
                                client.publish(power_from_battery_topic, v)
                                client.publish(power_battery_topic, -v)
                            else:
                                client.publish(power_from_battery_topic, 0)
                        print(
                            f"SOC retrieved: {soc} | power_to_battery: {v if i == 20 and o == 40 else 0} | "
                            f"power_from_battery: {-v if i == 40 and o == 20 else 0} | " 
                            f"power-battery: {v if i == 20 and o == 40 else 0} " 
                        )

                        client.disconnect()
                    else:
                        debug_print("SOC not found.")
                else:
                    debug_print(f"Failed to retrieve final data: {final_data_response.get('message')}")
            else:
                debug_print(f"Failed to fetch final data. Status Code: {response_final.status_code}")

# Main logic
if not token:
    debug_print("No token found. Requesting a new one.")
    token = request_new_token()

if token:
    if not sid:
        # Use the token to send a request for the SID
        url_station = "https://neapi.hoymiles.com/pvmc/api/0/station/select_by_page_c"
        headers_with_auth = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': token
        }

        data_station = {
            "page": 1,
            "page_size": 50
        }

        response_station = requests.post(url_station, json=data_station, headers=headers_with_auth)

        if response_station.status_code == 200:
            station_data = response_station.json()
            debug_print(f"SID retrieved: {station_data}")
            if station_data.get("status") == "0" and "data" in station_data:
                sid = station_data["data"].get("list", [{}])[0].get("sid")
                if sid:
                    debug_print(f"SID retrieved: {sid}")
                    save_sid_to_config(sid)
                else:
                    debug_print("SID not found in station data response.")
            else:
                debug_print(f"Failed to retrieve station data: {station_data.get('message')}")
                token = request_new_token()
        else:
            debug_print(f"Failed to fetch station data. Status Code: {response_station.status_code}")
            token = request_new_token()
    else:
        debug_print("SID loaded from config.")

    try:
        if sid:
            while True:
                # Log the start timestamp
                print(f"running at: {datetime.now().isoformat()}")
                send_final_request()
                time.sleep(request_interval_seconds)

    except KeyboardInterrupt:
        debug_print("\nScript terminated by user (Ctrl+C). Exiting gracefully.")
