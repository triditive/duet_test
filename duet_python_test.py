import pycurl
import urllib
import json

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
     # 'ip': "192.168.1.100",

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


def duet_get_model(config, api_path, debug=False):
    """ https://duet3d.dozuki.com/Wiki/Gcode#Section_M409_Query_object_model
        Parameters
        K"key" Key string, default empty
        F"flags" Flags string, default empty
        Examples

        M409 K"move.axes" F"f" ; report all frequently-changing properties of all axes
        M409 K"move.axes[0] F"v,n,d4" ; report all properties of the first axis, including values not normally reported, to a maximum depth of 4
        M409 K"move.axes[].homed" ; for all axes, report whether it is homed
        M409 K"#move.axes" ; report the number of axes
        M409 F"v" ; report the whole object model to the default depth
    """

    execute_url = "http://%s/rr_model?%s" % (config['ip'], api_path)
    ret = duet_get_url(config, execute_url, is_json=True)
    if not ret:
        print_alert(" No found !")
        return False

    if debug:
        print(json.dumps(ret, sort_keys=False, indent=4))

    return ret


def duet_get_analog(config, pin):
    ret = duet_get_model(config, "key=sensors.analog[" + str(pin) + "]", True)
    if not ret or not ret['result']:
        return None

    return ret['result']['lastReading']


def duet_get_digital(config, pin):
    ret = duet_get_model(config, "key=sensors.gpIn[" + str(pin) + "]", True)
    if not ret or not ret['result']:
        return None

    return ret['result']['value']


def get_status(config):
    #print("+ STATUS")
    execute_url = "http://%s/rr_status?type=3" % (config['ip'])
    ret = duet_get_url(config, execute_url, is_json=True)
    if not ret:
        return False

    return ret


def split_malformed_json_line(line):
    array_jsons = []
    c = 0
    pos = 0
    for ch in line:
        if ch == '{':
            if c == 0:
                c_start = pos
            c += 1
        elif ch == '}':
            c -= 1
            if c == 0:
                js = line[c_start:pos + 1]
                array_jsons.append(js)

        pos += 1
    return array_jsons


def duet_parse_json(lines, json_key):
    """ This is a hack to take into a count the malformed JSON returned
        It should be either carriage return separated or comma separated in an array.

        Therefore we have to split by groups of { }
        I could write a regex to extract json
    """
    count = 0

    for r in lines:
        r_strip = r.strip()
        if len(r_strip) == 0:
            continue

        if r_strip[0] != '{':
            continue

        try:
            jsons = split_malformed_json_line(r)
            for p in jsons:
                print("[" + p + "]")
                jdict = json.loads(p)
                if jdict['key'] == json_key:
                    return jdict

        except Exception as err:
            print_alert(" FAILED PARSING " + str(err))
            pass

    return None


def run_gcode_wait_for_response(config, gcode, regex=None,
                    filter=None, output_debug=True,
                    is_json=False, json_key=None):
    """ Runs GCODE on duet and waits for a response, due the variety of random response types this function is a bit overloaded
        - We use a simple filter for simple text,
        - A regex for something more complicated that we really want to check and get a value from
        - Sensors will return a JSON, with a key on then that we can check
            For sensors, it is better to use the rr_model call
            https://duet3d.dozuki.com/Wiki/Object_Model_of_RepRapFirmware

        This function should gracefully fail or check again
        It has a timeout defined in the config
    """

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

    ####### OUTPUT FOR DEBUG ######
    count = 0
    for r in sp:
        if len(r.strip()) != 0:
            print(str(count) + ": " + r)
            count += 1

    ##### JSON HACKING PARSING #####
    if is_json:
        return duet_parse_json(sp, json_key)

    ###### REGEX PARSING ############
    if regex:
        matches = re.finditer(regex, ret, re.MULTILINE)
        return matches

    ###### SIMPLE FILTER PARSING #####
    if not filter:
        if output_debug:
            print(ret)
        return ret

    res = []
    try:
        if output_debug:
            print_tx("RESPONSE BEGIN")

        count = 0
        for r in sp:
            r_strip = r.strip()
            if len(r_strip) != 0:
                print(str(count) + ": " + r.strip())
                if filter and r.startswith(filter):
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


def get_pin_state(config, gcode, key):
    """
    get_pin_state(config, pin_id = "sensors.gpIn[0]")
        We expect a sensor reading, therefore a key with the sensor on it as json format

        Command: 'M409 K"sensors.gpIn[0]"'
        Result: {"key":"sensors.gpIn[0]","flags":"","result":{"value":0}}
    """
    response = run_gcode_wait_for_response(config, gcode, is_json=True, json_key=key)

    if not response:
        print_alert(" NO RESPONSE ")
        return None
    else:
        print(json.dumps(response, sort_keys=False, indent=4))

        if (key.startswith("sensors.analog")):
            value = response['result']['lastReading']
            return value

        if (key.startswith("sensors.gpIn")):
            value = response['result']['value']
            return value

        value = response
        print_h1(" Value " + str(value))
        return value

    if not response:
        return None

    return response


def send_message(config, msg):
    """  """
    response = run_gcode_wait_for_response(config, "M117", msg)
    if not response:
        return False

    print("response");
    return response


#######################################################################################

# COMMAND QUEUE TO READ THE DELTA CONFIGURATION
ret = get_current_delta_configuration(config)

send_message(config, "HELLO WORLD!")

# COMMAND QUEUE TO READ ENDSTOPS
ret = get_endstops_status(config)

# COMMAND QUEUE TO READ POSITION
ret = get_current_position(config)

# USE THE COMMAND QUEUE TO READ PIN
# Example reading sensors running the GCODE (Don't use)
# Very flaky, don't use.

#get_pin_state(config, 'M409 K"sensors.gpIn[0]"', "sensors.gpIn[0]")
#get_pin_state(config, 'M409 K"sensors.analog[1]"', "sensors.analog[1]")
#get_pin_state(config, 'M409 K"sensors" F"f,v,n,d8"', "sensors")

# RAW READ OF SENSOR PIN 0

# Example reading the sensors through the rr_model API
ret = duet_get_model(config, "key=sensors.analog[1]", True)
ret = duet_get_model(config, "key=sensors.gpIn[0]", True)

# EXAMPLE READ THE AXIS INFORMATION

ret = duet_get_model(config, "key=move.axes[1]&flags=1", True)

# EXAMPLE READ A DIGITAL PIN USING THE RR_MODEL

value = duet_get_digital(config, 0)
if value == 0:
    print_alert(" Pin is off ")
elif value == 1:
    print_alert(" Pin is on ")
else:
    print_alert(" Error reading pin ")

# EXAMPLE READ AN ANALOG PIN USING THE RR_MODEL

value = duet_get_analog(config, 1)
if value == None:
    print_alert(" Error reading pin ")
else:
    print_alert(" Pin last value is " + str(value))


# Get endstops & flags
# ret = duet_get_model(config, "key=sensors.endstops&flags=v,d3", True)

ret = duet_get_model(config, "key=sensors.endstops", True)

print_h1(" END" )