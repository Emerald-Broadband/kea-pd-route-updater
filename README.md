# Kea Prefix Delegation Route Updater

This module runs as a hook in the Kea DHCPv6 server to manage routes on layer 3 switches that do not handle Prefix Delegation route insertion on their own. It is in active use with PicOS v4.4.x and should be applicable (perhaps with minor changes) to other Linux-based platforms.

## Configuration

The hook may be activated on the `kea-dhcp6` with this configuration in `kea-dhcp6.conf`.

```
"hooks-libraries": [
    {
        "library": "/usr/local/lib/kea/hooks/libdhcp_run_script.so",
        "parameters": {
            "name": "/root/update-v6.py",
            "sync": false
        }
    }
],
```
Adjust the library path and `name` parameter to match your file locations. Note that `update-v6.py` must be executable by the user that runs the `kea-dhcp6` server.

The script requires some configuration parameters as a JSON object stored in `/tmp/lease_routes_config.json`. You can adjust that location in the script itself if you'd like it in another location.

That configuration must look like (adjusted for your desired configuration):

```
{
    "ROUTES_FILE": "/tmp/lease_routes.json",
    "LOG_FILE": "/tmp/dhcp_script.log",
    "SSH_IDENTITY_FILE": "/root/.ssh/id_ed25519",
    "SSH_USERNAME": "kea",
    "MANAGED_SWITCHES": ["2604:2940::ffff:ffff:ffff:fffe", "fd00::1"]
}
```

The example above uses shortened addresses in the `MANAGED_SWITCHES` parameter for privacy. Kea uses the fully expanded addresses in the `QUERY6_REMOTE_ADDR`, so you will need to also.

The SSH parameters need to match what you have configured on your switches. In this case, there is a `kea` user with authentication set to use the key stored in `SSH_IDENTITY_FILE`. The `kea` user must have `sudo` access on the switch (to insert and delete routes).

The `ROUTES_FILE` is used to avoid sending unnecessary commands to the switch. When a route is added by this script, it is logged to that file and will only be re-applied (deleted and added) if it changes.

The `LOG_FILE` records all of the actions received and taken by the script.
