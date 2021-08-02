# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

i.e. `<Major version>.<Minor version>.<Patch version>`

## [Unreleased] - TBA

### Added
- maninpualation class api
- inbound normalization and outbound manipulation
- add realm for routing vars
- unlimited/bypass capacity check (lower-bound>=-1)
- codec AMR-NB, AMR-WB
- media profile with dtmf mode, media mode(proxy,bypass,transcode), codec negotiation algo (generous, greedy, scrooge), VAD, CNG
- support distribution algorithm

### Changed
- ansible role convention
- no remove verbose log input data
- replace local var by NgVars
- use pubsub instead of queue
- from host with hostname after fresh restart

### Fixed
- Fix unintended field for gateways update

## [v0.3.0] - 2021-06-12

### Added
*Initial release*

- NAT Traversal Capabilities
- Call Party Translatation
- Protocol translations between UDP, TCP, TLS
- Powerful built-in routing engine
- Dynamic Load Balancing, Failover, Distribution
- Topology hiding by back to back user agent
- Encryption of signaling TLS and media SRTP
- Access Control List
- Auto Control Network Firewall
- Resource allocation
- Rate limiting include call per second (cps), concurrent calls
- Traffic Optimization by token bucket and leaky bucket
- Media encoding/decoding SRTP/RTP
- DTMF RFC2833
- Media Codec transcoding: G711A/U, G729, OPUS
- Tones and announcements (Early Media)
- Data and fax interworking
- Flexible JSON for Call Detail Record (CDR), Send CDR to HTTP API, enabling customized/3rd-party usage such as databases, data analysis or billing purpose. 
- Network capture support: Live Capture and Intergrated with Homer
