import traceback
import json
import copy

import redis
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from utilities import logify, get_request_uuid


# api router declaration
fsxmlrouter = APIRouter()

# template location 
templates = Jinja2Templates(directory="templates/callengine")