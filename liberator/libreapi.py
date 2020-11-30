

from pydantic import BaseModel, validator
from typing import Optional, List
from fastapi import APIRouter, Request, Response

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, NODENAME, CLUSTERNAME, CLUSTER_MEMBERS,
                    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logger, get_request_uuid, int2bool, bool2int, rembytes


# api router declaration
librerouter = APIRouter()

# ACL/RECOGNITION
# DISTRIBUTOR
# GATEWAYS
# SIP PROFILE

@librerouter.get("/preconfig", status_code=200)
def preconfig():
    return {
        "nodename": NODENAME,
        "cluster": CLUSTERNAME,
        "application": _APPLICATION,
        'swversion': _SWVERSION,
        "description": _DESCRIPTION
    }


class CodecModel(BaseModel):
    name: str
    desc: str
    data: List[str]

class CapacityModel(BaseModel):
    name: str
    desc: str
    cps: int
    capacity: int

class ConditionModel(BaseModel):
    target: str
    pattern: str

class ActionModel(BaseModel):
    target: str
    pattern: str
    replacement: str

class TranslationModel(BaseModel):
    name: str
    desc: str
    condition: ConditionModel
    action: ActionModel
    antiaction: ActionModel

class FlowRule(BaseModel)
    name: str
    desc: str
    condition: List[ConditionModel]
    action: ActionModel
    antiaction: ActionModel