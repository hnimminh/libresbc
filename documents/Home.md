<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square"><br/><br/>
<p align="center"> <img width="296px" src="https://user-images.githubusercontent.com/58973699/126869145-9c15755b-426b-40dd-a478-56b28c98f6e9.png" alt=""></p>

## Introduction
A Session Border Controller (SBC) is a network function which secures voice over IP (VoIP) infrastructures while providing interworking between incompatible signaling messages and media flows (sessions) from end devices or application servers. SBCs are employed in Enterprise infrastructures or any carrier network delivering commercial residential, business, fixed-line or mobile VoIP services. They are typically deployed at both the network edge and at carrier interconnects, the demarcation points (borders) between their users and other service providers. Communications service providers and enterprises both make use of SBCs. Service providers deploy SBCs at access, core and interconnect network borders. Enterprises typically deploy SBCs at the edge of the enterprise network, for example as the termination point for a SIP trunking service.

## Functions
<p align="center"> <img width="800" src="https://user-images.githubusercontent.com/58973699/126863556-8f38531c-f086-45cb-a286-5639a3768747.png"></p>

* **Security** - The main reason Session Border Controllers are used within businesses is for security. SBC protects against hacking, cyber-attacks and any bad influence from outside the network. The SBC is essentially a more efficient and secure firewall. Where a firewall is in place for most general systems and networks, an SBC is specifically designed to protect your personal network. The SBC also encrypts data, signaling and media, preventing outside influences from monitoring your information and activity.  

* **Interoperability**
SBCs allow different parts of a network to communicate and share data with each other. An example of how SBCs do this is through SIP normalisation. A key role of an SBC is to mediate SIP communication between different devices, systems or gateways that use or ‘speak’ SIP differently. The SBC manipulate (or normalises) and translates SIP signaling and messaging so everything is properly communicated. 

* **Quality of service (QoS)** - The SBC implements the Quality of Service or QoS policy, that measures the performance of a service or network. The SBC regulates and prioritises rate limiting, traffic policing, call admission control and data flows that come into or go out of the network.  

* **Routing** - SBCs route the call across network interfaces by multiple logic factor.

* **Media Process** This includes supporting the calls, data and fax interworking and media transcoding. Media encryption, Ringtone, Announcement. Media transcoding is where the SBC translates between different codecs. Essentially, codecs convert voice and video signals for digital transmission. The SBC can translate these through transcoding, resulting in better sound quality and reducing network bandwidths. This in turn results in a better call experience for your colleagues and clients.

## Architecture
<p align="center"> <img width="800" src="https://user-images.githubusercontent.com/58973699/126864923-f77931f0-406a-47e7-b346-17956919341f.png"></p>

## Frequent Asked Questions
1. What is different between SBC and SIP Proxy and Firewall?
> * Proxy handle SIP signalling only
> * SBC handle SIP signalling and Media as well
> * Firewall handle the network function on for layer 2-4 only
> 
> Below is table of function comparison
> Function | Firewall | Proxy | SBC
> :--- | :---: | :---: | :---:
> Layer 2-4 Packet Filtering | ✅ | ✅ | ✅
> Route/NAT | ✅ | ✅ | ✅
> Prevent DSS/DDOS attach | ✅ | ✅ | ✅
> SIP Header Manipulation /Interoperability |  | ✅ | ✅
> SIP Routing |  | ✅ | ✅
> Toll Fraud Protection |  | ✅ | ✅
> Topology Hiding |  |  | ✅
> Media Transcoding/Transcyption |  |  | ✅
> QoS Measurement & Reporting |  |  | ✅

2. How does LibreSBC detect and defend attack?
> Here is some techniques, LibreSBC use to protect system:
> * Built-in IP Firewall
> * IP white/black list
> * Brute-force attack prevention
> * Rate Limit: Concurrent call, Call per Second
> * Authentication

3. How does LibreSBC limit call traffic?
> LibreSBC implement these algorithm to control traffic:
> * Call rate limit (cps)
> * Constant rate traffic shaping
> * Concurrent call limit

4. What is Topology Hiding? Why we need it?
> SIP is complicated protocol with network information in header to control call flow, Naturally, It will record and expose network topology in message. Topology Hiding help to strip/substitutes internal network information before send to outside world. Yay, That is security harden.

5. Can I use LibreSBC to perform load balancing, fail-over?
> Yes, LibreSBC can be act as an `load balancer`, `healthcheck` - *select healthy server* , `failover` - *go to secondary if primary down* for far-end entities

6. Can I deploy LibreSBC on cloud and/or bare-metal server?
> Absolutely Yes, LibreSBC can be deployed and work well on cloud, bare-metal server or containers. We have some deployment on Digital Ocean, VMware, Docker and AWS already.

7. What is performance of LibreSBC?
> In reality performance typically depend on 2 main factors which are SIP Signaling and RTP Media, These typically translate into calls per second (cps) and concurrent calls respectively. Additionally, the performance also impact by database usage (connections, propagation delay..) with configuration query, cache, etc and of course machine resources (Memory, CPU, Bandwidth, Read/Write IO..). 
>
> There's an informal load test has been done on standalone server,
> * System Under Test
>   * OS: Debian 4.19.132-1 x86_64 (10.6)
>   * CPU: Intel(R) Xeon(R) CPU X5670 @ 2.93GHz
>   * RAM: 8GB; SSD: 128GB
> * Result:
>   * 50 call per second, 1000 concurrent call
>   * Used Memory: 1730M, CPU Load: 26%, Call Duration: 600 seconds
> 
> The performance can be increase by some way like increase machine resources or using LibreSBC clusters.




