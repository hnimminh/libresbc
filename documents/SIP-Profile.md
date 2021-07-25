<img src="https://img.shields.io/badge/STATUS-WORK IN PROGRESS-orange?style=flat-square">

## Introduce
**SIP Profile/Interface** is an application layer interface logically residing over a network interface. The SIP profile defines the transport addresses (IP address and port) upon which the LibreSBC receives and sends SIP messages and RTP packets as well as related rtp media and signalling setting. You can define a SIP profile for each network to which the LibreSBC is connected. SIP profile support UDP, TCP and TLS transport. In addition to defining a SIP Profile's IP address might be defined by NetAlias API.

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/sipprofile-BLUE?style=for-the-badge&logo=Safari">

Consider any setting that you want to add, following is the configuration parameters:

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of profile (unique)    
desc         |`string` | Description                     
user_agent   |`string` | The value will be displayed as User-Agent in SIP header. Default is `LibreSBC`
sdp_user     |`string` | The username of the o= and s= fields in SDP body
context      |`string` `required` | The dialplan context of SIP profile
tls          |`bool` | Enable TLS transport




*continue..*
```diff
-remove
+add
#commend
@@ at
```

💮♦️ ⛩️ 🗽 🌏 ⚡🌸☎️ ☎️. ♦️♥️ 🚩 🧭
🔺 🔻 ⭕ 🔴 🔵 🔹🔸 ❄️ 💢 ⭐ 🔴 🟥 🔸🔴 🌀  → 