<p align="center"> <img width="800" src="https://user-images.githubusercontent.com/58973699/126865893-fe63be54-da33-4be4-9906-a6ecb0ed8fc2.png"></p>

**Access Service is an component that enable the LibreSBC communicate to public network (internet) and serve the access functions include:**
* Registrar
* Location Service
* Authentication
* Routing
* Topology Hiding
* Multi-Domain Policy
* Antiflooding
* Bruteforce Prevention
* Microsoft Teams Direct Routing (*under-development*)

## Setting

## Access Service
<img src="https://img.shields.io/badge/API-/libreapi/access/service-BLUE?style=for-the-badge&logo=Safari">
 
Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name of access service
desc       |`string`| description
server_header|`string`|Server Header
transports|`list`|list of binding transport protocol `udp` `tcp` `tls`
sip_address|`string`|IP address via NetAlias use for SIP Signalling
antiflooding|`map`| security function for antifloofing/ddos
authfailure|`map`| security function for authentication failure/bruteforce/intrusion detection
attackavoid|`map`| security function for attack avoidance
blackips|`list`|denied ip list
whiteips|`list`|allowed ip list
domains|`list`|list of policy domain

**Antiflooding Map**
Parameter  | Category           | Description                     
:---       |:---                |:---            
sampling|`int`|sampling time unit (in second)
density|`int`|number of request that allow in sampling time, then will be ignore within window time
window|`int`|evaluated window time in second
threshold|`int`|number of flooding threshold that will be banned
bantime|`int`|firewall ban time in second

**Authfailure Map**
Parameter  | Category           | Description                     
:---       |:---                |:---            
window|`int`|evaluated window time in second
threshold|`int`|number of authentication failure threshold that will be banned
bantime|`int`|firewall ban time in second

**Attackavoid Map**
Parameter  | Category           | Description                     
:---       |:---                |:---            
window|`int`|evaluated window time in second
threshold|`int`|number of request threshold that will be banned
bantime|`int`|firewall ban time in second


### Access Domain Policy
<img src="https://img.shields.io/badge/API-/libreapi/access/domainpolicy-BLUE?style=for-the-badge&logo=Safari">

Parameter  | Category           | Description                     
:---       |:---                |:---                             
domain     |`string` `required` | The sip domain
srcsocket  |`map`| listen socket of sip between proxy and b2bua
dstsocket  |`map`| forward socket of sip between proxy and b2bua

**srcsocket/dstsocket Map**

Parameter  | Category           | Description                     
:---       |:---                |:---                             
ip     |`string` `required` | ip address

### Access User Directory
<img src="https://img.shields.io/badge/API-/libreapi/access/directory/user-BLUE?style=for-the-badge&logo=Safari">

Parameter  | Category           | Description                     
:---       |:---                |:---                             
domain     |`string` `required` | The sip domain
id  |`string` `required`| user identifier
secret  |`string` `required`| password of digest auth for inbound