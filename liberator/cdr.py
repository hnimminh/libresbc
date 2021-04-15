import time
import traceback
from threading import Thread
from math import exp
from random import randint, choice, shuffle
from datetime import datetime, date, timezone
import json

import requests
import redis

SIP_DISPOSITION_MAP = {
    0: "FAILURE",
    100: "TRYING",
    180: 'RINGING', 
    181: 'FORWARDING',
    182: 'QUEUED',
    183: 'PROGRESS',
    199: 'TERMINATION',
    200: 'ANSWERED',
    202: 'ANSWERED',
    204: 'ANSWERED',
    301: 'REDIRECTION',
    302: 'REDIRECTION',
    305: 'REDIRECTION',
    380: 'REDIRECTION',
    400: 'CONGESTION',
    401: 'CONGESTION' ,
    402: 'CONGESTION',
    403: 'CONGESTION',
    404: 'CONGESTION',
    405: 'CONGESTION',
    406: 'CONGESTION',
    407: 'CONGESTION',
    408: 'NOANSWER',
    409: 'CONGESTION',
    410: 'CONGESTION',
    411: 'CONGESTION',
    413: 'CONGESTION',
    414: 'CONGESTION',
    415: 'CONGESTION',
    420: 'CONGESTION',
    480: 'NOANSWER',
    481: 'CONGESTION',
    482: 'CONGESTION',
    483: 'CONGESTION',
    484: 'CONGESTION',
    485: 'CONGESTION',
    486: 'BUSY',
    487: 'CANCEL',
    488: 'CONGESTION',
    500: 'CONGESTION',
    501: 'CONGESTION',
    502: 'CONGESTION',
    503: 'CONGESTION',
    504: 'CONGESTION',
    505: 'CONGESTION',
    580: 'CONGESTION',
    600: 'BUSY',
    603: 'CONGESTION',
    604: 'CONGESTION',
    606: 'CONGESTION'
}