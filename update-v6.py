#!/usr/bin/env python3

import os
import sys
import logging
import subprocess
import json
from datetime import datetime

# Define the configuration file path
CONFIG_FILE = '/tmp/lease_routes_config.json'

# Read configuration from file
def read_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file {CONFIG_FILE} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {CONFIG_FILE}")
        sys.exit(1)

# Load configuration
config = read_config()

# Extract configuration variables
ROUTES_FILE = config['ROUTES_FILE']
LOG_FILE = config['LOG_FILE']
SSH_IDENTITY_FILE = config['SSH_IDENTITY_FILE']
SSH_USERNAME = config['SSH_USERNAME']
MANAGED_SWITCHES = config['MANAGED_SWITCHES']

# Initialize logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def unknown_handle(*args):
    logging.error(f"Unhandled function call {args}")
    sys.exit(123)

def lease6_renew():
    query6_remote_addr = os.environ.get('QUERY6_REMOTE_ADDR')
    lease6_address = os.environ.get('LEASE6_ADDRESS')
    lease6_prefix_len = os.environ.get('LEASE6_PREFIX_LEN')
    logging.info('RENEW - ' + lease6_address + '/' + lease6_prefix_len + ' by ' + query6_remote_addr)
    logging.debug('RENEW - ' + str(os.environ))
    return 0

def lease6_rebind():
    logging.debug('REBIND - ' + str(os.environ))
    return 0

def lease6_expire():
    logging.debug('EXPIRE - ' + str(os.environ))
    return 0

def lease6_recover():
    logging.debug('RECOVER - ' + str(os.environ))
    return 0

def check_route_exists(address, prefix_len):
    try:
        with open(ROUTES_FILE, 'r') as f:
            routes = json.load(f)
    except FileNotFoundError:
        return False

    for route in routes:
        if route['address'] == address and route['prefix_len'] == int(prefix_len):
            return route['gateway']  # Return the cached gateway
    return False

def update_route(address, prefix_len, new_gateway):
    try:
        with open(ROUTES_FILE, 'r') as f:
            routes = json.load(f)
    except FileNotFoundError:
        routes = []

    for route in routes:
        if route['address'] == address and route['prefix_len'] == int(prefix_len):
            cached_gateway = route['gateway']
            if cached_gateway != new_gateway:
                # Remove the old route entry
                routes.remove(route)
                # Add the updated route
                new_route = {'address': address, 'prefix_len': int(prefix_len), 'gateway': new_gateway}
                routes.append(new_route)
                # Write the updated list back to the file
                with open(ROUTES_FILE, 'w') as f:
                    json.dump(routes, f, indent=4)
                return True  # Updated successfully
            return False  # Gateway is the same, so no update needed
    # If no existing route, add new route
    new_route = {'address': address, 'prefix_len': int(prefix_len), 'gateway': new_gateway}
    routes.append(new_route)
    with open(ROUTES_FILE, 'w') as f:
        json.dump(routes, f, indent=4)
    return True  # Added new route

def leases6_committed():
    query6_remote_addr = os.environ.get('QUERY6_REMOTE_ADDR')
    leases6_at1_address = os.environ.get('LEASES6_AT1_ADDRESS')
    leases6_at1_prefix_len = os.environ.get('LEASES6_AT1_PREFIX_LEN')
    leases6_at0_address = os.environ.get('LEASES6_AT0_ADDRESS')

    if query6_remote_addr in MANAGED_SWITCHES:
        if leases6_at1_address and leases6_at1_prefix_len and leases6_at0_address:
            cached_gateway = check_route_exists(leases6_at1_address, leases6_at1_prefix_len)

            if cached_gateway:
                if cached_gateway != leases6_at0_address:
                    # Gateway has changed, remove the old route
                    del_cmd = f"sudo ip route del {leases6_at1_address}/{leases6_at1_prefix_len} via {cached_gateway}"
                    logging.info(f"COMMITTED - Removing old route: {del_cmd}")
                    subprocess.run(["ssh", "-i", SSH_IDENTITY_FILE, f'{SSH_USERNAME}@{query6_remote_addr}', del_cmd])
                else:
                    logging.info(f"COMMITTED - Route {leases6_at1_address}/{leases6_at1_prefix_len} already exists with correct gateway. Skipping.")
                    return 0

            # Add or update the route
            add_cmd = f"sudo ip route add {leases6_at1_address}/{leases6_at1_prefix_len} via {leases6_at0_address}"
            logging.info(f"COMMITTED - Adding/Updating route: {add_cmd}")
            subprocess.run(["ssh", "-i", SSH_IDENTITY_FILE, f'{SSH_USERNAME}@{query6_remote_addr}', add_cmd])

            if update_route(leases6_at1_address, leases6_at1_prefix_len, leases6_at0_address):
                logging.info("COMMITTED - Route added/updated in JSON file")
            else:
                logging.error("COMMITTED - Failed to update JSON file")
        else:
            logging.warning("COMMITTED - LEASES6_AT1_ADDRESS, LEASES6_AT1_PREFIX_LEN, or LEASES6_AT0_ADDRESS is empty. Skipping route operations.")
    return 0

def lease6_release():
    logging.info('RELEASE - ' + str(os.environ))
    return 0

def lease6_decline():
    logging.info('DECLINE - ' + str(os.environ))
    return 0

if __name__ == "__main__":
    function_map = {
        "lease6_renew": lease6_renew,
        "lease6_rebind": lease6_rebind,
        "lease6_expire": lease6_expire,
        "lease6_recover": lease6_recover,
        "leases6_committed": leases6_committed,
        "lease6_release": lease6_release,
        "lease6_decline": lease6_decline
    }

    if len(sys.argv) < 2:
        unknown_handle("No function specified")

    function_name = sys.argv[1]
    if function_name in function_map:
        sys.exit(function_map[function_name]())
    else:
        unknown_handle(sys.argv)

