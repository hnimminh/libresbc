<a href="https://github.com/hnimminh/libresbc" target="_blank">
  <p align="center"> <img width="200px" src="https://user-images.githubusercontent.com/58973699/126869145-9c15755b-426b-40dd-a478-56b28c98f6e9.png" alt=""> </p>
</a>

<p align="center">
  <a href="https://github.com/hnimminh/libresbc/stargazers" target="_blank">
    <img src="https://badgen.net//github/stars/hnimminh/libresbc?color=cyan" alt="">
  </a>
  <a href="https://github.com/hnimminh/libresbc/commits/master" target="_blank">
    <img src="https://badgen.net/github/last-commit/hnimminh/libresbc?icon=github" alt="">
  </a>
  <a href="LICENSE.md" target="_blank">
    <img src="https://badgen.net/badge/license/MIT/blue" alt="">
  </a>
  <a href="https://github.com/hnimminh/libresbc/releases" target="_blank">
    <img src="https://badgen.net/github/tag/hnimminh/libresbc" alt="">
  </a>
</p>

<h1 align="center">LibreSBC</h1>
<h2 align="center">The Open Source Session Border Controller</h2>
<p align="left"><b>LibreSBC is a open-source Session Border Controller provide robust security, simplified interoperability, advanced session management, high performance, scale of carrier-grade and reliability for voice over IP (VoIP) infrastructures. LibreSBC designed to typically deployed at the network edge, the demarcation points (borders) among networks/environments.</b><br></p>


<br>

<h2>Contributing</h2>
All kinds of contributions are very welcome and appreciated !

If you want to contribute time to LibreSBC then here's a list of suggestions to get you started :

1. Star 🌟 the project.
2. Help people in the [issues](https://github.com/hnimminh/libresbc/issues) by sharing your knowledge and experience.
3. Find and report issues.
4. Influence the future of LibreSBC with feature requests.


**You can also contribute money to help secure LibreSBC's future.**

<p align="center">
  <a href="https://www.paypal.com/paypalme/hnimminh" target="_blank">
    <img src="https://user-images.githubusercontent.com/58973699/130890970-ad7f3be3-42c4-4a21-8e28-27dda9c603e3.png" height="54" alt="Paypal">
  </a>
  <a href="https://www.patreon.com/hnimminh" target="_blank">
    <img src="https://user-images.githubusercontent.com/58973699/121804772-32781280-cc72-11eb-8707-29200197649d.png" height="54" alt="Patreon">
  </a>
</p>

<br>
<p align="center"> <img width="960px" src="https://user-images.githubusercontent.com/58973699/129482983-111fef1a-fa46-450f-b6ed-e8166bc49c15.png" alt=""> </p>

<br>

## Table of Contents
- [Why](#why)
- [Architecture](#architecture)
- [Functions](#functions)
  - [Connectivity & Compatibility](#connectivity-&-compatibility)
  - [Security](#security)
  - [Quality of service](#quality-of-service)
  - [Media services](#media-services)
  - [Intergration](#intergration)
  - [High Avaibility](#high-avaibility)
- [Documents](#documents)
- [Roadmap](#roadmap)
- [Deployment](#deployment)
- [Performance Test](#performance-test)
- [License](#license)

<br>

## Why
* Free & Open: It's free and always free for everyone
* Comunity & Majoirity: Standing on the shoulders of giants, Kamailio and FreeSWITCH
* Customisability: Make it do what you want
* Capability: Carrier-grade 

## Upcomming Features
- [x] Documentation
- [x] Access Layer
- [ ] TLS/SSL with LetEncrypt support
- [ ] MsTeam Direct Routing Intergaration
- [ ] STIR/SHAKEN and Identity Assurance
- [ ] Dashboard WebUI

## Architecture
![image](https://user-images.githubusercontent.com/58973699/121683376-7c80bd00-cae7-11eb-8161-c03022f9bf6d.png)

## Functions
SBCs commonly maintain full session state and offer the following functions:

### Connectivity & Compatibility
Allow multiple networks to communicate through the use of a variety of techniques such as:
* Advanced [NAT](https://en.wikipedia.org/wiki/Network_address_translation) Traversal Capabilities
* [SIP](https://en.wikipedia.org/wiki/Session_Initiation_Protocol) normalization, SIP message and header manipulation
* Call Party Translatation
* [VPN](https://en.wikipedia.org/wiki/Virtual_private_network) connectivity
* Protocol translations between [UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol), [TCP](https://en.wikipedia.org/wiki/Transmission_Control_Protocol) & [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security)
* Powerful built-in routing engine.
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
* Media Codec transcoding: [G711A/U](https://en.wikipedia.org/wiki/G.711), [G729](https://en.wikipedia.org/wiki/G.729), [OPUS](https://en.wikipedia.org/wiki/Opus_(audio_format)), [AMR](https://en.wikipedia.org/wiki/Adaptive_Multi-Rate_audio_codec), [G.722.2 AMR-WB](https://en.wikipedia.org/wiki/Adaptive_Multi-Rate_Wideband)
* Tones and announcements (Early Media)
* Data and fax interworking
* Support multiple Media mode: Proxy, Bypass, Transcode
* Voice Activity Detection [VAD](https://en.wikipedia.org/wiki/Voice_activity_detection)
* Confort Noise Generation [CNG](https://en.wikipedia.org/wiki/Comfort_noise)

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

## Documents
[Wiki](https://github.com/hnimminh/libresbc/wiki)

## Roadmap
[Development & Roadmap](https://github.com/hnimminh/libresbc/projects/1)

## Discussions
[Discussions](https://github.com/hnimminh/libresbc/discussions)

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

