import logging.handlers
import os
import sys

import threading
import time
import datetime
import math
import logging

import re

g_debug_header = None
# g_debug_header = 2

import shutil

DIS_WIDE=25

def get_timestamp(d=None):
    if not d:
        d = datetime.datetime.now()

    unixtime = time.mktime(d.timetuple())
    return int(unixtime)

last_refresh = get_timestamp()

def get_tm():
    return "[" + str(get_timestamp()) + "] "


loggers = {}


def get_logger(log, text):
    global loggers

    if text == '':
        log = "GENERAL"

    log_name = str(log)
    if log_name in loggers:
        return loggers[log_name]

    my_logger = logging.getLogger(log_name)
    my_logger.setLevel(logging.DEBUG)

    ensure_dir("./logs/")

    ARM_LOG = 'logs/arm_%s.log' % log_name
    handler = logging.handlers.RotatingFileHandler(
        ARM_LOG, maxBytes=4*1024*1024, backupCount=5)

    my_logger.addHandler(handler)
    loggers[log_name] = my_logger
    return my_logger


def ensure_dir(f):
    """Ensure that a needed directory exists, creating it if it doesn't"""
    # print("Ensure dir")
    try:
        d = os.path.dirname(f)
        # print(d)

        if not os.path.exists(d):
            os.makedirs(d)

        return os.path.exists(f)
    except OSError:
        if not os.path.isdir(f):
            raise
    return None


def json_clean(obj):
    """ Returns the same object, but it ignores all the serialization problems """
    from flask import json
    return json.loads(json.dumps(obj, default=lambda o: '<not serializable>'))


def header_function(header_line):
    print("Not adding header_line")
    matches = re.finditer(regex, header_line, re.MULTILINE)


vt_lock = threading.Lock()


def get_time_HHMMSS(value):
    import math

    try:
        value = int(value)
    except ValueError:
        return "00:00:00"

    h = math.floor(value/(60*60))
    m = math.floor((value/60))%60
    s = math.floor(value)%60

    ret = ""
    if (h<10):
        ret+="0" + str(h)
    else:
        ret+=str(h)

    ret+=":"
    if (m<10):
        ret+="0" + str(m)
    else:
        ret+=str(m)

    ret+=":"
    if (s<10):
        ret+="0" + str(s)
    else:
        ret+=str(s)

    return ret


def month_string_to_number(string):
    m = { 'jan': 1, 'feb': 2, 'mar': 3,
        'apr':4, 'may':5, 'jun':6,
         'jul':7, 'aug':8, 'sep':9,
         'oct':10, 'nov':11, 'dec':12 }

    s = string.strip()[:3].lower()
    try:
        out = m[s]
        return out
    except:
        raise ValueError('Not a month')

def get_timestamp_verbose(str):
    try:
        value = int(str)
        return value
    except ValueError:
        pass

    try:
        month = month_string_to_number(str)
        d = datetime.datetime.now()
        return get_timestamp(d.replace(day=1, month=month))
    except ValueError:
        pass

    now = get_timestamp()
    if str == "now":
        return now

    if str == "month":
        return now - 31*24*60*60

    regex = re.compile(r"(\d+) month")
    months = regex.search(str)
    if months:
        return now - 31*24*60*60 * int(months.group(1))

    if str == "week":
        return now - 7*24*60*60

    regex = re.compile(r"(\d+) week")
    weeks = regex.search(str)
    if weeks:
        return now - 7*24*60*60 * int(weeks.group(1))

    if str == "day":
        return now - 24*60*60

    regex = re.compile(r"(\d+) day")
    days = regex.search(str)
    if days:
        return now - 24*60*60 * int(days.group(1))

    if str == "hour":
        return now - 60*60

    regex = re.compile(r"(\d+) hour")
    hours = regex.search(str)
    if hours:
        return now - 60*60 * int(hours.group(1))

    if str == "minute":
        return now - 60

    regex = re.compile(r"(\d+) min")
    mins = regex.search(str)
    if mins:
        return now - 60 * int(mins.group(1))

    print("Didn't understand " + str)
    return now


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def vt_clear():
    sys.stdout.write('\033[2J')

# http://ascii-table.com/ansi-escape-sequences.php
def vt_set_scroll(row_start, row_end):
    SCROLL = "\033[%d:%dr" % (row_start, row_end)
    sys.stdout.write(SCROLL)


def vt_set_cursor(x, y):
    ESCAPE = "\033[%d:%df" % (x, y)
    sys.stdout.write(ESCAPE)


def vt_set_cursor_horizontal(x):
    ESCAPE = "\033[%dG" % (x)
    sys.stdout.write(ESCAPE)


def write_header(header):
    if header == "":
        return ""

    c = 0
    if (str(header).isdigit()):
        c = DIS_WIDE * (int(header))
    else:
        c = 100

    return ("\033[%dG" % (c))

invalidate = False

def print_h(header, s, character, text='', in_place=False):
    global g_debug_header
    global last_refresh, invalidate

    if g_debug_header and g_debug_header != header:
        return ""

    if text == '' and not isinstance(header, int):
        text = header
        header = ''

    if (isinstance(text, str)):
        text = text.strip()

    out = ""
    if header!='':
        out += str(header)
        out += ": "

    if (not in_place and len(text) > 40):
        vt_lock.acquire()
        sys.stdout.write(write_header(header) + out + text + "\n")
        sys.stdout.flush()
        vt_lock.release()
        return out

    l = len(text)

    if l > 0:
        n = (s - (l + 2)) / 2
    else:
        n = s / 2

    if (math.ceil(n)!=n):
        carry = 1
    else:
        carry = 0

    c = n
    while c > 0:
        out += character
        c -= 1

    if l > 0:
        out += " %s " % text
        c = n + l + 2
    else:
        c = n

    while c < s - carry:
        out += character
        c += 1

    vt_lock.acquire()
    sys.stdout.write(write_header(header))
    sys.stdout.write(out)
    if (not in_place):
        sys.stdout.write("\n")
    else:
        invalidate=True

    sys.stdout.flush()
    vt_lock.release()

    last_refresh = get_timestamp()
    return out

def _(s): return s.encode('utf-8').decode('unicode_escape');

ESC = '\u001B['
cursorSavePosition = _(ESC + ('s'));
cursorRestorePosition = _(ESC + ('u'));
eraseLine = _(ESC + '2K');

def cursorTo(x, y = None):
  return _(ESC + str(y + 1) + ';' + str(x + 1) + 'H');

def print_xy(x, y, text='', color=bcolors.OKBLUE):
    global last_refresh

    elapsed = get_timestamp() - last_refresh
    if elapsed<=2:
        return

    # We cancel the autorefresh in the terminal if there were no regular prints in x minutes
    if elapsed > 60:
        TERM_WIDTH = -1

    sys.stdout.write(cursorSavePosition + cursorTo(x,y) + color + text + bcolors.ENDC + cursorRestorePosition)
    sys.stdout.flush()

def print_xy_slot(slot, y, text='', color=bcolors.OKBLUE):
    print_xy(slot * DIS_WIDE, y, text, color)

def erase_line(y):
    sys.stdout.write(cursorSavePosition + cursorTo(1,y) + eraseLine + cursorRestorePosition)
    sys.stdout.flush()

def print_h1(slot, text='', in_place=False):
    global g_debug_header, invalidate
    if g_debug_header and g_debug_header != slot:
        return

    if invalidate and not in_place:
        sys.stdout.write("\n")
        sys.stdout.flush()
        invalidate=False

    sys.stdout.write(bcolors.WARNING)
    get_logger(slot, text).info(get_tm() + bcolors.WARNING +
        print_h(slot, 28, "#", text, in_place) + bcolors.ENDC)
    sys.stdout.write(bcolors.ENDC)


def print_invalidate(forced = False):
    elapsed = get_timestamp() - last_refresh
    if elapsed<2 or elapsed>600:
        return

    for y in range(10):
        erase_line(y)


def print_b(slot, text=''):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    sys.stdout.write(bcolors.FAIL)
    get_logger(slot, text).error(get_tm() + bcolors.OKBLUE +
                           text + bcolors.ENDC)
    sys.stdout.write(bcolors.ENDC)


def print_e(slot, text=''):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    sys.stdout.write(bcolors.FAIL)
    get_logger(slot, text).error(get_tm() + bcolors.FAIL +
                           print_h(slot, 30, "!", text) + bcolors.ENDC)
    sys.stdout.write(bcolors.ENDC)


def print_ce(slot, text=''):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    sys.stdout.write(bcolors.OKBLUE)
    get_logger(slot, text).error(get_tm() + bcolors.OKBLUE +
                           print_h(slot, 35, " ", text.upper()) + bcolors.ENDC)
    sys.stdout.write(bcolors.ENDC)


def print_tx(slot, text='', log=True, MAX_TEXT_SIZE=80, in_place=False):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    vt_lock.acquire()
    sys.stdout.write(bcolors.OKBLUE)

    if text!='':
        sys.stdout.write(write_header(slot))
    else:
        text = slot
        slot = ""
        log = False

    if (log):
        get_logger(slot, text).info(get_tm() + bcolors.OKBLUE + "%s: %s" %
                              (str(slot), text) + bcolors.ENDC)

    sys.stdout.write("%s: %s" % (slot, text))
    if not in_place:
        sys.stdout.write("\n")

    sys.stdout.write(bcolors.ENDC)
    vt_lock.release()


def print_h2(slot, text='', in_place=False):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    get_logger(slot, text).info(get_tm() + print_h(slot, 30, "*", text, in_place))


def print_h3(slot, text='', in_place=False):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    get_logger(slot, text).info(get_tm() + print_h(slot, 25, "-", text, in_place))


def print_h4(slot, text='', in_place=False):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    get_logger(slot, text).info(get_tm() + print_h(slot, 20, "+", text, in_place))


def print_h5(slot, text='', in_place=False):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    get_logger(slot, text).info(get_tm() + print_h(slot, 20, "-", text, in_place))


def print_alert(slot, text=''):
    global g_debug_header
    if g_debug_header and g_debug_header != slot:
        return

    print("")
    sys.stdout.write(bcolors.HEADER)
    if text!='':
        get_logger(slot, text).error(get_tm() + bcolors.HEADER +
                            print_h(slot, 40, "%", " ") + bcolors.ENDC)

    get_logger(slot, text).error(get_tm() + bcolors.HEADER +
                           print_h(slot, 40, "%", text) + bcolors.ENDC)

    if text!='':
        get_logger(slot, text).error(get_tm() + bcolors.HEADER +
                               print_h(slot, 40, "%", " ") + bcolors.ENDC)
    print("")
    sys.stdout.write(bcolors.ENDC)


def set_cursor(x, y):
    sys.stdout.write('\033[%d;%dH' % (x, y))


def dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))


def print_debug(s):
    out = ":".join("{:02x}".format(ord(c)) for c in s)
    print(out)
    print("[%s]" % (s))
    return out


############### KEYBOARD CONTROL #################################


def split_tmpinto_len(s, l=2):
    """ Split a string into chunks of length l """
    return s.splitlines()
    # return [s[i:i+l] for i in range(0, len(s), l)]


def get_response_error(slot, error, data= {}):
    # logging.error("%s: %s" %(slot, error))
    # print("!!!!!!!! ERROR %d [%s] !!!!!!" %(slot, error))
    return {"id": slot,
            "error": error,
            "status": "Error",
            "data": data,
            "ok": 0
            }


def get_response_success(slot, result):
    # logging.info("%s: %s" %(slot, result))
    # print("*********** SUCCESS %d [%s] *********** " %(slot, result))
    return {"id": slot,
            "status": "success",
            "result": result,
            "ok": 1,
            }


def get_last_file_time(file_name):
    try:
        t = os.path.getmtime(file_name)
        # print("last modified: %s" % time.ctime(t))
        return t
    except Exception as e1:
        return -1


TERM_WIDTH=-1
TERM_HEIGHT=-1
init_terminal = False

def terminal_update():
    global TERM_WIDTH, TERM_HEIGHT, DIS_WIDE, init_terminal

    try:
        width, height = shutil.get_terminal_size((250, 40))

        if width==TERM_WIDTH and height==TERM_HEIGHT:
            DIS_WIDE = math.floor((width - 25)/9)
            return

        if init_terminal and TERM_WIDTH != -1 and width != 317:
            vt_clear()
            init_terminal = False

        TERM_WIDTH=width
        TERM_HEIGHT=height

        DIS_WIDE = math.floor((TERM_WIDTH - 25)/9)

        if not init_terminal:
            print(" TERMINAL " + str(TERM_WIDTH) + "," + str(TERM_HEIGHT))
            print(" DIS " + str(DIS_WIDE))

        init_terminal = True
    except Exception as err:
        print(" Failed Terminal update ");

terminal_update()