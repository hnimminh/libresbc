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
  <a href="https://github.com/hnimminh/libresbc/releases" target="_blank">
    <img src="https://badgen.net/github/tag/hnimminh/libresbc" alt="">
  </a>
    <a href="LICENSE.md" target="_blank">
    <img src="https://badgen.net/badge/license/MIT/ffd700" alt="">
  </a>
  <a href="#" target="_blank">
    <img src="https://img.shields.io/badge/clone-22/week-00afd7?style=plastic&logo=GitHubActions">
    <img src="https://img.shields.io/badge/view-1415/week-d70000?style=plastic&logo=monkeytie">
  </a>
</p>

<h1 align="center">LibreSBC</h1>
<h2 align="center">The Open Source Session Border Controller</h2>
<p align="left"><b>LibreSBC is an open-source Session Border Controller that provides robust security, simplified interoperability, advanced session management, high performance, highly reliable and carrier grade for voice over IP (VoIP) transport. LibreSBC is designed to be deployed at the network edge, to protext at the demarcation points (borders) facilitate session normalization, hide topologies, perform packet switching operations and handle packet switching tasks.</b><br></p>


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
* Free & Open source: It's open source and always free for everyone
* Backed By a Proven and Solid Community: Standing on the shoulders of giants, Kamailio and FreeSWITCH
* Customizable: Make it your solution. 
* Capable:Scalable, robust and carrier grade software SBC.

## Upcomming Features
- [x] Documentation
- [x] Access Layer
- [ ] TLS/SSL with LetEncrypt support
- [ ] MsTeam Direct Routing Integrations
- [ ] STIR/SHAKEN and Identity Assurance
- [ ] Dashboard WebUI
- [ ]Clustered Containerization

## Architecture
![image](https://user-images.githubusercontent.com/58973699/121683376-7c80bd00-cae7-11eb-8161-c03022f9bf6d.png)

## Functions
Session Management, Packet Switching, Session Normalization, B2BUA:

### Connectivity & Compatibility
SIP and Media Transport via:
* Advanced [NAT](https://en.wikipedia.org/wiki/Network_address_translation)Traversal.
* [SIP](https://en.wikipedia.org/wiki/Session_Initiation_Protocol) normalization, body and header fixup. 
* Caller/Calling Party ID Management
* [VPN](https://en.wikipedia.org/wiki/Virtual_private_network) connectivity
* Session Interop and State Manager [UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol), [TCP](https://en.wikipedia.org/wiki/Transmission_Control_Protocol) & [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security)
* SIP Routing via a proven engine.
* API Integrations for extensibility [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol)
* Highly reliable with load balancing, High Availability, with failover.

### Security:
Enterprise Security Features:
* Denial of Service protection ([DoS](https://en.wikipedia.org/wiki/Denial-of-service_attack)) 
* Media Anchoring and RTP/SRTP Session Management
* Malformed Setup Protections
* Active Call Ferrying with B2BUA and Topology hiding/Fixup ([B2BUA](https://en.wikipedia.org/wiki/Back-to-back_user_agent))
* Secure RTP with encryption/State Management ([SRTP](https://en.wikipedia.org/wiki/Secure_Real-time_Transport_Protocol))
* IP Blacklisting
* Fail2Ban and Auto Blocking Policies
* Advanced SIP Policy Management

### Quality of service 
The [QoS](https://en.wikipedia.org/wiki/Quality_of_service) Packet Prioritization:
* Bandwidth Reservation and Priority Routing
* [Rate limiting](https://en.wikipedia.org/wiki/Call_volume_(telecommunications)) and Costing by weight/distance/Route.
* Route Optimization  [token bucket](https://en.wikipedia.org/wiki/Token_bucket) and [leaky bucket](https://en.wikipedia.org/wiki/Leaky_bucket)
* [ToS](https://en.wikipedia.org/wiki/Type_of_service)/[DSCP](https://en.wikipedia.org/wiki/Differentiated_services) bit setting

### Media services
Session Media Handling:
* Media encoding/decoding ([SRTP](https://en.wikipedia.org/wiki/Secure_Real-time_Transport_Protocol)/[RTP](https://en.wikipedia.org/wiki/Real-time_Transport_Protocol))
* [DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) relay and interworking include In-Band Signaling (touch tones), Out-of-Band Signaling ([RFC2833](https://www.ietf.org/rfc/rfc2833.txt)) and SIP INFO Method
* Media Codec transcoding: [G711A/U](https://en.wikipedia.org/wiki/G.711), [G729](https://en.wikipedia.org/wiki/G.729), [OPUS](https://en.wikipedia.org/wiki/Opus_(audio_format)), [AMR](https://en.wikipedia.org/wiki/Adaptive_Multi-Rate_audio_codec), [G.722.2 AMR-WB](https://en.wikipedia.org/wiki/Adaptive_Multi-Rate_Wideband)
* Tones and announcements (Early Media)
* T.38 Support for FoIP (Fax-Over-IP)
* Proxy/Flow/Policy based transport
* Voice Activity Detection [VAD](https://en.wikipedia.org/wiki/Voice_activity_detection)
* Confort Noise Generation [CNG](https://en.wikipedia.org/wiki/Comfort_noise)

### Integrations
3rd party integrations via API for extensibility
* Billing and CDR via HTTP(S) API using JSON standards([CDR](https://en.wikipedia.org/wiki/Call_detail_record))
* Standards Based API
* MOS Scoring and SIP Capture via Homer [Homer](https://sipcapture.org/) 
* [SNMP](https://en.wikipedia.org/wiki/Simple_Network_Management_Protocol) and/or [Prometheus](https://prometheus.io/) SNMP Monitoring

### High Avaibility
* [Distributed System](https://en.wikipedia.org/wiki/Distributed_computing)
* High Availability w/ Active-Active [Cluster](https://en.wikipedia.org/wiki/Computer_cluster) Cluster.
* Heartbeat checks and Dead Host Detection

## Documents
[Wiki](https://github.com/hnimminh/libresbc/wiki)

## Roadmap
[Development & Roadmap](https://github.com/hnimminh/libresbc/projects/1)

## Discussions
[Discussions](https://github.com/hnimminh/libresbc/discussions)

## Performance Test
* System Specifications 
  * OS: Debian 4.19.132-1 x86_64 (10.6)
  * CPU: Intel(R) Xeon(R) CPU X5670  @ 2.93GHz
  * RAM: 8GB; SSD: 128GB
* Benchmark Results:
  * 50 call per second (setup), 1000 concurent call
  * Memory Utilization: 1730M
   * CPU Load: 26%
   * Call Duration: 600 seconds

## License
[MIT](./LICENSE)

