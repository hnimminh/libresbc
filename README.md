[![N|Solid](https://repository-images.githubusercontent.com/286777346/c7ff7f80-2215-11eb-963f-acb53c9acd8f)](https://github.com/hnimminh/libresbc)


# Libre Session Border Controller
LibreSBC is a [Session Border Controller](https://en.wikipedia.org/wiki/Session_border_controller), a network function which secures voice over IP (VoIP) infrastructures while providing interworking between incompatible signaling messages and media flows (sessions) from end devices or application servers. LibreSBC designed to employed in Enterprise infrastructures or any carrier network delivering commercial residential, or typically deployed at both the network edge and at carrier interconnects, the demarcation points (borders) between private production environment and other service providers.

## Functions
SBCs commonly maintain full session state and offer the following functions:

### Connectivity & Compatibility
Allow multiple networks to communicate through the use of a variety of techniques such as:
* Advanced [NAT](https://en.wikipedia.org/wiki/Network_address_translation) Traversal Capabilities
* [SIP](https://en.wikipedia.org/wiki/Session_Initiation_Protocol) normalization, SIP message and header manipulation
* Call Party Translatation
* [VPN](https://en.wikipedia.org/wiki/Virtual_private_network) connectivity
* Protocol translations between [UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol), [TCP](https://en.wikipedia.org/wiki/Transmission_Control_Protocol) & [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security)
* Powerful built-in routing module.
* Allowing control routing by 3rd-party software via [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol)
* Dynamic Load Balancing, Failover, Distribution

### Security:
Protect the network and other devices from:
* Malicious attacks such as a denial-of-service attack ([DoS](https://en.wikipedia.org/wiki/Denial-of-service_attack)) or distributed DoS
* Toll fraud via rogue media streams
* SIP Malformed Packet Protection
* Topology hiding by back to back user agent ([B2BUA](https://en.wikipedia.org/wiki/Back-to-back_user_agent))
* Encryption of signaling (via TLS) and media ([SRTP](https://en.wikipedia.org/wiki/Secure_Real-time_Transport_Protocol))
* Access Control List
* Auto Control Network Firewall
* SIP Firewall Level

### Quality of service 
The [QoS](https://en.wikipedia.org/wiki/Quality_of_service) policy of a network and prioritization of flows is usually implemented by the SBC. It can include such functions as:
* Resource allocation
* [Rate limiting](https://en.wikipedia.org/wiki/Call_volume_(telecommunications)) include call per second (cps), concurrent calls (concurency)
* Traffic Optimization by [token bucket](https://en.wikipedia.org/wiki/Token_bucket) and [leaky bucket](https://en.wikipedia.org/wiki/Leaky_bucket)
* [ToS](https://en.wikipedia.org/wiki/Type_of_service)/[DSCP](https://en.wikipedia.org/wiki/Differentiated_services) bit setting

### Media services
Offer border-based media control and services such as:
* Media encoding/decoding ([SRTP](https://en.wikipedia.org/wiki/Secure_Real-time_Transport_Protocol)/[RTP](https://en.wikipedia.org/wiki/Real-time_Transport_Protocol))
* [DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) relay and interworking include In-Band Signaling (touch tones), Out-of-Band Signaling ([RFC2833](https://www.ietf.org/rfc/rfc2833.txt)) and SIP INFO Method
* Media Codec transcoding: [G711A/U](https://en.wikipedia.org/wiki/G.711), [G729](https://en.wikipedia.org/wiki/G.729), [OPUS](https://en.wikipedia.org/wiki/Opus_(audio_format)).
* Tones and announcements
* Data and fax interworking

### Intergration
Support to intergrate with 3rd-party system or customer function easily
* Flexible JSON for Call Detail Record ([CDR](https://en.wikipedia.org/wiki/Call_detail_record)), Send CDR to HTTP API, enabling customized/3rd-party usage such as databases, data analysis or billing purpose. 
* Customization routing mechanism via HTTP API
* Network capture support: Live Capture and Intergrated with [Homer](https://sipcapture.org/) 
* [SNMP](https://en.wikipedia.org/wiki/Simple_Network_Management_Protocol) and/or [Prometheus](https://prometheus.io/) monitoring

### High Avaibility
* [Distributed System](https://en.wikipedia.org/wiki/Distributed_computing)
* Active-Active [Cluster](https://en.wikipedia.org/wiki/Computer_cluster) Concept
* Healthcheck and Failure Autodetection

## Architecture
![image](https://user-images.githubusercontent.com/58973699/116818193-56850600-ab94-11eb-8a15-cbe25724c27f.png)

## Performance Test
* System Under Test
  * OS: Debian 4.19.132-1 x86_64 (10.6)
  * CPU: Intel(R) Xeon(R) CPU X5670  @ 2.93GHz
  * RAM: 8GB; SSD: 128GB
* Result:
  * 50 call per second, 1000 concurent call
  * Used Memory: 1730M, CPU Load: 26%, Call Duration: 600 seconds

## License
[MIT](./LICENSE)