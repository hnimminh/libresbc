[![N|Solid](https://repository-images.githubusercontent.com/286777346/c7ff7f80-2215-11eb-963f-acb53c9acd8f)](https://github.com/hnimminh/libresbc)


# LibreSBC - Libre Session Border Controller
LibreSBC is a Session Border Controller, a network function which secures voice over IP (VoIP) infrastructures while providing interworking between incompatible signaling messages and media flows (sessions) from end devices or application servers. LibreSBC designed to employed in Enterprise infrastructures or any carrier network delivering commercial residential, or typically deployed at both the network edge and at carrier interconnects, the demarcation points (borders) between their users and other service providers.

## FEATURES
SBCs commonly maintain full session state and offer the following functions:

* Connectivity & Compatibility – allow multiple networks to communicate through the use of a variety of techniques such as:
  * Advanced NAT Traversal Capabilities
  * SIP normalization via SIP message and header manipulation
  * Call Party Translatation
  * VPN connectivity
  * Protocol translations between UDP, TCP & TLS
  * Built-in Powerful routing module.
  * Allowing control routing by 3rd-party software with via HTTP
  * Dynamic Load Balancing, Failover, Distribution

* Security – protect the network and other devices from:
  * Malicious attacks such as a denial-of-service attack (DoS) or distributed DoS
  * Toll fraud via rogue media streams
  * SIP Malformed Packet Protection
  * Topology hiding by back to back user agent (B2BUA)
  * Malformed packet protection
  * Encryption of signaling (via TLS) and media (SRTP)
  * Access Control List
  * Smart IP Firewall

* Quality of service – the QoS policy of a network and prioritization of flows is usually implemented by the SBC. It can include such functions as:
  * Resource allocation
  * Rate limiting include call per second (cps), concurrent calls (ccs)
  * Traffic Optimization by token bucket and leaky bucket
  * Network capture support: Live Capture and Intergrated with [Homer](https://sipcapture.org/)
  * ToS/DSCP bit setting
  * Self-Monitering System
  * Flexible JSON Call Detail Record (CDR), able to store in rawfile or http hook.


* Media services – offer border-based media control and services such as:
  * Media encoding/decoding (SRTP/RTP)
  * DTMF relay and interworking
  * Media Codec transcoding: ALAW, ULAW, G729, OPUS.
  * Tones and announcements
  * Data and fax interworking

* High Avaibility
  * Distributed System 
  * Active-Active Clustering Concept
  * Healthcheck and Autodetect Failure

## Architecture
(updating..)

## Performance Test
* System Under Test
  * OS: Debian 4.19.132-1 x86_64 (10.6)
  * CPU: Intel(R) Xeon(R) CPU X5670  @ 2.93GHz
  * RAM: 8 G
  * SSD: 128 GB
* Result:
  * 50 call per second, 1000 concurent call
  * Used Memory: 1730M, CPU Load: 26, Duration: 600 seconds

## LICENSE

[MIT](./LICENSE)