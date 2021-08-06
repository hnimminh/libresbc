<img src="https://img.shields.io/badge/STATUS-NEVER DONE-d90000?style=flat-square">

## Party Number
caller id number type apply following these order:
* manipulation setting
* interconnection setting
* gateways setting

## Privacy Header
* PID = PID
* PAI = PID + OriginPrivacy[id]
* RPID = RPID, RPID + Privacy

```shell
PID + Privacy[no] → PAI + Privacy[none]
PID + Privacy[no] + OriginPrivacy[number] → PAI + Privacy[id]
PID + Privacy[yes] → PAI + Privacy[id]
PID + Privacy[number] → PAI + Privacy[id]
PID + Privacy[name] → PAI + Privacy[none]
PID + Privacy[name] + OriginPrivacy[number] → PAI + Privacy[id]
PID + Privacy[full] → PAI + Privacy[id]

PID + OriginPrivacy[number] → PAI + Privacy[id]
PID + OriginPrivacy[screen] → PAI + Privacy[none]
PID + OriginPrivacy[name or <invalid>] → PID + Privacy[none]
PID + OriginPrivacy[screen+name] → PAI + Privacy[none]
PID + OriginPrivacy[screen+name+number] → PAI + Privacy[id]

OP:screen,name,number → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=full
OP:name,number → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=no;privacy=full
OP:name → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=no;privacy=name
OP:number → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=no;privacy=full
OP:screen → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=off

P:name → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=name
P:number → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=full
P:no → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=off
P:full → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=full
P:yes → Remote-Party-ID: "Donald Trump" <sip:6533123456789@HOTS>;party=calling;screen=yes;privacy=full
```
<p align="right"><i>Make with ❤️ in Saigon 🇻🇳<i/></p>
