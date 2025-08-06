<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square"><br/><br/>


This tutorial focus on LibreSBC configuration only. The example demonstrate for scenario of receiving inbound call from Twilio to your PBX via LibreSBC, the configuration for revert direction (outbound call from your PBX to Twilio) would be similar.

## Environment
### Twilio
* SIP IP addresses
  * 54.172.60.0/30
  * 54.244.51.0/30
  * 54.171.127.192/30
  * 35.156.191.128/30
  * 54.65.63.192/30
  * 54.169.127.128/30
  * 54.252.254.64/30
  * 177.71.206.192/30

* RTP IP addresses
  * 54.172.60.0/23
  * 34.203.250.0/23
  * 54.244.51.0/24
  * 54.171.127.192/26
  * 52.215.127.0/24
  * 35.156.191.128/25 
  * 3.122.181.0/24
  * 54.65.63.192/26
  * 3.112.80.0/24
  * 54.169.127.128/26
  * 3.1.77.0/24
  * 54.252.254.64/26
  * 3.104.90.0/24
  * 177.71.206.192/26
  * 18.228.249.0/24

* Codec: When Twilio directs incoming traffic from the PSTN to your communications infrastructure, it will send PCMU and PCMA in the following order in the SDP parameter.
  * PCMU
  * PCMA

* Numbering Plan: E164+  ;eg: +6566123456 (send out)

### PBX
* SIP IP address: 10.10.10.20
* RTP IP address: 10.10.10.20
* Codec:
  * G729
  * PCMA
  * PCMU
* Numbering Plan: E164 ;eg: 6566123456 (expect to receive)

### LibreSBC
* Eth1: 172.17.17.2 (1-to-1 NAT with WAN IP 1.2.3.4)
* Eth2: 10.10.10.10


![example](https://user-images.githubusercontent.com/58973699/201487283-c626765c-e245-45bd-8be0-7f67e778f182.png)


## Configuration:
The configuration should follow the procedure on this [page](https://github.com/hnimminh/libresbc/wiki/Configuration)
### Node
```
{
  "name": "libresbc",
  "members": [
    "devsbc"
  ],
  "rtp_start_port": 10000,
  "rtp_end_port": 30000,
  "max_calls_per_second": 100,
  "max_concurrent_calls": 3000
}
```

### Net Alias
* Network Alias for connecting to public network (WAN)
```
{
  "name": "public",
  "desc": "public facing",
  "addresses": [
    {
      "member": "devsbc",
      "listen": "172.17.17.2",
      "advertise": "1.2.3.4"
    }
  ]
}
```

* Network Alias for connecting to private network (LAN)
```
{
  "name": "private",
  "desc": "private facing",
  "addresses": [
    {
      "member": "devsbc",
      "listen": "10.10.10.10",
      "advertise": "10.10.10.10"
    }
  ]
}
```

### SIP Profile
* SIP Profile for connecting to public network (WAN)
```
{
  "name": "external",
  "desc": "SIP Public Profile",
  "user_agent": "LibreSBC",
  "sdp_user": "LibreSBC",
  "local_network_acl": "rfc1918.auto",
  "addrdetect": "autonat",
  "enable_100rel": true,
  "ignore_183nosdp": true,
  "sip_options_respond_503_on_busy": false,
  "disable_transfer": true,
  "manual_redirect": true,
  "enable_3pcc": false,
  "enable_compact_headers": false,
  "dtmf_type": "rfc2833",
  "media_timeout": 0,
  "rtp_rewrite_timestamps": true,
  "context": "carrier",
  "sip_port": 5060,
  "sip_address": "public",
  "rtp_address": "public",
  "tls": false,
  "tls_only": false,
  "sips_port": 5061,
  "tls_version": "tlsv1.2"
}
```

* SIP Profile for connecting to private network (LAN)
```
{
  "name": "internal",
  "desc": "SIP Private Profile",
  "user_agent": "LibreSBC",
  "sdp_user": "LibreSBC",
  "local_network_acl": "rfc1918.auto",
  "addrdetect": "autonat",
  "enable_100rel": true,
  "ignore_183nosdp": true,
  "sip_options_respond_503_on_busy": false,
  "disable_transfer": true,
  "manual_redirect": true,
  "enable_3pcc": false,
  "enable_compact_headers": false,
  "dtmf_type": "rfc2833",
  "media_timeout": 0,
  "rtp_rewrite_timestamps": true,
  "context": "carrier",
  "sip_port": 5060,
  "sip_address": "private",
  "rtp_address": "private",
  "tls": false,
  "tls_only": false,
  "sips_port": 5061,
  "tls_version": "tlsv1.2"
}
```

### Media Class
* Media profile for Twilio connection 
```
{
  "name": "pcm",
  "desc": "pstn media profile",
  "codecs": [
    "PCMA",
    "PCMU"
  ]
}
```


* Media profile for PBX connection
```
{
  "name": "pbx",
  "desc": "pbx media profile",
  "codecs": [
    "G729",
    "PCMA",
    "PCMU"
  ]
}
```

### Capacity Class
Declare limitation of traffic (or set to -1 for unlimited traffic)
```
{
	"name": "small",
	"desc": "smb traffic",
	"cps": 2,
	"concurentcalls": 10
}
```
 

### Translation Class
Since there is a mismatch of number format between Twilio (E164+) and PBX (E164), we will need a translation to fix the compatible beetwen them

```
{
  "name": "noplus",
  "desc": "Remove Plug Sign",
  "caller_number_pattern": "^\\+?([0-9]+)$",
  "destination_number_pattern": "^\\+?([0-9]+)$",
  "caller_number_replacement": "%{1}",
  "destination_number_replacement": "%{1}",
  "caller_name": "_auto"
}
```

### Gateway
Declare PBX as a gateway
```
{
  "name": "PBXGW",
  "desc": "PBX Gateway",
  "username": "none",
  "password": "none",
  "proxy": "10.10.10.20",
  "port": 5060,
  "transport": "udp",
  "do_register": false,
  "caller_id_in_from": true,
  "cid_type": "none",
  "ping": 600
}
```

### Outbound Interconnection
```
{
  "name": "PBX",
  "desc": "PBX Server",
  "sipprofile": "internal",
  "distribution": "weight_based",
  "sipaddrs": [
    "10.10.10.20/32",
  ],
  "rtpaddrs": [
    "10.10.10.20/32"
  ],
  "media_class": "pbx",
  "capacity_class": "small",
  "translation_classes": ["noplus"],
  "manipulation_classes": [],
  "privacy": ["none"],
  "cid_type": "none",
  "nodes": [
    "_ALL_"
  ],
  "enable": true,
  "gateways": [
    {
      "name": "PBXGW",
      "weight": 1
    }
  ]
}
```

### Routing 

The routing logic for this is simple, all trafic from twilio will route to PBX. 

```
{
  "name": "topbx",
  "desc": "route call to PBX",
  "action": "route",
  "routes": {
    "primary": "PBX",
    "secondary": "PBX",
    "load": 100
  }
}
```
In case, you need more complicated routing, example route base on destination, caller number, etc .. please refer to [Routing Wiki](https://github.com/hnimminh/libresbc/wiki/Routing) for more detail

### Inbound Interconnection
Declare inbound traffic from Twilio
```
{
  "name": "TWILIO",
  "desc": "Twilio",
  "sipprofile": "external",
  "routing": "topbx",
  "sipaddrs": [
    "54.172.60.0/30",
    "54.244.51.0/30",
    "54.171.127.192/30",
    "35.156.191.128/30",
    "54.65.63.192/30",
    "54.169.127.128/30",
    "54.252.254.64/30",
    "177.71.206.192/30"
  ],
  "rtpaddrs": [
    "54.172.60.0/23",
    "34.203.250.0/23",
    "54.244.51.0/24",
    "54.171.127.192/26",
    "52.215.127.0/24",
    "35.156.191.128/25 ",
    "3.122.181.0/24",
    "54.65.63.192/26",
    "3.112.80.0/24",
    "54.169.127.128/26",
    "3.1.77.0/24",
    "54.252.254.64/26",
    "3.104.90.0/24",
    "177.71.206.192/26",
    "18.228.249.0/24"
  ],
  "ringready": false,
  "media_class": "pcm",
  "capacity_class": "small",
  "translation_classes": [],
  "manipulation_classes": [],
  "authscheme": "IP",
  "nodes": [
    "_ALL_"
  ],
  "enable": true
}
```

