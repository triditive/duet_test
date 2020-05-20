import pycurl
import urllib

from io import BytesIO
from print_helper import *

try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

import json
import time

config = {
    'ip': "192.168.1.100",
    'interface': "docker0",
     #'interface': "tun0",                 # VPN
     #'interface': "enp5s0",               # Ethernet 192.168.0.10
     'interface': "wlx001986d03a9c",      # Ethernet 192.168.1.10
    #'interface': "lo",                    # Local, doesn't work
    'timeout': 5,
}

print("\n")
print_h1("+ DUET HELPER ")

print_h1(" CURL INTERFACE " + config['interface'])

#print_tx("  Just run GCODE and gets a response from the DUET \n")

def duet_get_url(config, url, is_json=True, Verbose=False):
    import json
    buffer = BytesIO()

    try:
        c = pycurl.Curl()
        c.setopt(c.HTTPHEADER, ["Content-type: application/json"])
        c.setopt(c.URL, url)
        c.setopt(c.VERBOSE, Verbose)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.INTERFACE, config['interface'])
        c.perform()
        c.close()

    except pycurl.error as e:
        print_alert("PYCURL ERROR")
        return False

    ret = buffer.getvalue().decode('iso-8859-1')

    try:
        if is_json:
            ret = json.loads(ret)
        else:
            # print(" REPLY [" + ret.strip() + "] ")
            return ret

    except Exception as e:
        print_alert(" JSON Exception " + str(e))
        return False

    return ret

def get_status(config):
    #print("+ STATUS")
    execute_url = "http://%s/rr_status?type=3" % (config['ip'])
    ret = duet_get_url(config, execute_url, is_json=True)
    if not ret:
        return False

    return ret

def run_gcode_wait_for_response(config, gcode, regex=None, filter=None, output_debug=True):
    import re

    response = ""

    if output_debug:
        print("\n")
        print_h1("RUN : " + gcode)

    status = get_status(config)
    if not status:
        return False

    command_id = status['seq']

    execute_url = "http://%s/rr_gcode?" % (config['ip'])
    data = urllib.parse.urlencode({'gcode': gcode})

    ret = duet_get_url(config, execute_url + data, is_json=True)
    if not ret:
        return False

    #print("+ OK")

    if 'buff' not in ret:
        if output_debug:
            print("! Failed to store the gcode in the buffer ")

        return False

    if output_debug and ret['buff'] != 250:
        print_h1("+ Buffered " + str(ret['buff']))

    # We give 0.25s of wait, the buffer overflows if I query too fast.
    time.sleep(0.25)

    count = config['timeout']
    while count > 0:
        status = get_status(config)
        if not status:
            if output_debug:
                print_h1(" Not status ")
            return False

        seq = status['seq']

        if seq != command_id:
            if output_debug:
                print_h1(" FOUND RESPONSE " + str(seq))
            break

        if output_debug:
            print_h1(" WAIT " + str(count))

        time.sleep(0.5)
        count -= 1

    if count == 0:
        print_alert(" TIMEOUT ")
        return False

    execute_url = "http://%s/rr_reply" % (config['ip'])
    ret = duet_get_url(config, execute_url, is_json=False)
    if not ret or len(ret) == 0:
        print_alert("FAILED GETTING REPLY")
        return False

    sp = ret.split("\n")
    count = 0
    for r in sp:
        if len(r.strip()) != 0:
            print(str(count) + ": " + r.strip())
            count += 1

    if regex:
        matches = re.finditer(regex, ret, re.MULTILINE)
        return matches

    if not filter:
        if output_debug:
            print(ret)
        return ret

    res = []
    try:
        if output_debug:
            print_tx("RESPONSE BEGIN")

        sp = ret.split("\n")

        count = 0
        for r in sp:
            if len(r.strip()) != 0:
                print(str(count) + ": " + r.strip())
                if r.startswith(filter):
                    res.append(r)

            count += 1

        if output_debug:
            print_tx("RESPONSE END")

    except Exception as e:
        print_alert(" Exception ")
        print(str(e))

    return res

#######################################################################################

def get_current_position(config):
    """ X:0.000 Y:0.000 Z:342.183 E:0.000 E0:0.0 Count 43506 43506 43506 Machine 0.000 0.000 342.183 Bed comp 0.000 """

    regex = r"X:([\d.]+) Y:([\d.]+) Z:([\d.]+) E:([\d.]+) E0:([\d.]+) Count ([\d]+) ([\d]+) ([\d]+) Machine ([\d.]+) ([\d.]+) ([\d.]+) Bed comp ([\d.]+)"
    response = run_gcode_wait_for_response(config, "M114", regex, filter="X:")
    if not response:
        return False

    ret = []
    for matchNum, match in enumerate(response, start=1):
        g = match.groups()
        ret.append({
            'xyze': [ g[0], g[1], g[2], g[3] ],
            'e0': g[4],
            'count': [ g[5], g[6], g[7]],
            'machine': [ g[8], g[9], g[10]],
            'bed_comp': g[11],
        })

    print(json.dumps(ret, sort_keys=True, indent=4))
    return ret


def get_endstops_status(config):
    """ Endstops - X: not stopped, Y: not stopped, Z: not stopped, Z probe: not stopped """

    response = run_gcode_wait_for_response(config, "M119", filter="Endstops ")
    if not response:
        return False

    return response

def set_switch_io(config, pin, value):
    if value:
        value = "S255"
    else:
        value = "S0"

    return run_gcode_wait_for_response(config, "M42 P" + pin + " " + value)


def get_current_delta_configuration(config):
    """ Diagonals 227.400:227.400:227.400, delta radius 105.129, homed height 347.181, bed radius 110.0, X -0.077Â°, Y 0.290Â°, Z 0.000Â° """
    regex = r"Diagonals ([\d.]+):([\d.]+):([\d.]+), delta radius ([\d.]+), homed height ([\d.]+), bed radius ([\d.]+)"

    response = run_gcode_wait_for_response(config, "M665", regex=regex)
    if not response:
        return False

    ret = []
    for matchNum, match in enumerate(response, start=1):
        g = match.groups()
        ret.append({
            'diagonals': [ g[0], g[1], g[2] ],
            'delta_radius': g[3] ,
            'homed_height': g[4],
            'bed_radius': g[5],
        })

    print(json.dumps(ret, sort_keys=True, indent=4))
    return ret

def send_message(config, msg):
    """  """
    response = run_gcode_wait_for_response(config, "M117", msg)
    if not response:
        return False

    print("response");
    return response

#######################################################################################

#get_current_position(config)
#get_current_delta_configuration(config)

#######################################################################################

run_gcode_wait_for_response(config, "M408 S0")

count = 100
while count > 0:

    get_endstops_status(config)
    send_message(config, "HELLO WORLD!")

    get_current_position(config)
    get_current_delta_configuration(config)

    count -= 1