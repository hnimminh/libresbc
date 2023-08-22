# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

i.e. `<Major version>.<Minor version>.<Patch version>`

## [Unreleased] - TBA
- Fix jumps routing table
- Update CaptAgent to 6.4.1
- PreAnswer validation
- Support IPv6
- Fix routing recording typo match key
- Web Admin UI application
- Fix ansible compile codec amr
- Packages and distro label, thanks to @ciscomonkey
- Upgrate lib requests==2.22.0 -> 2.31.0, starlette==0.26.1 -> 0.27.0
- Additional acl/parse SIP settings

## [v0.6.0] - 2023-04-08
- Update Dev Env
- Unhandling loopback source when sbc under NAT #55
- Support configurable address detection #56
- Unix Socket RDB
- Improper name for intecon:out #64
- Swaping Auth realm updating sipprofile #65
- Inbound unaware/validate manipulation rule #67
- Null Leg Normalize #68
- Enable Local CDR (nice json)
- Support Call Routing via HTTP API
- Example for CDR convertion json-csv
- Support customize CDR file name and interval
- Fix routing block action invalid data #82
- Unable to delete unengaged routing table #80
- Support ignore ealry media to preanswer class #91
- Fix missing function early-media
- Upgrate lib starlette==0.14.2 -> 0.25.0, redis==3.5.2 -> 4.4.4
- Version fastapi starlette agreement 

## [v0.5.9] - 2022-07-26
- Fix #36 missing cmake for mod_g729
- Add self logo images
- Ansible lineinfile instead of shell sed #37
- Fix Captagent role misorder #40
- Fix Python pip3 install task missing package #41
- Enhance Deployment role
- API CORS #43
- Fix #51 [Deployement] FreeSWITCH require SignalWise PATs

## [v0.5.8] - 2021-09-26
- Fix #30 Inconsistent socket secret 
- Fix #31 Gateway not reload if previous reloaded
- Fix #32 Consolidate sip profile
- Change access username pattern [a-zA-Z]+ to [a-zA-Z0-9]+
- Fix #33 Nil type value if cidtype and not farend
- Fix missing module for kamailio build from source
- Remove total weight distributor #24
- Fix #25 no handle zero weight gateways/distributor

## [v0.5.7] - 2021-08-26
### Added
- Maninpualation class api
- Inbound normalization and outbound manipulation
- Add realm for routing vars
- Unlimited/bypass capacity check (lower-bound>=-1)
- Codec AMR-NB, AMR-WB
- Media profile with dtmf mode, media mode(proxy,bypass,transcode), codec negotiation algo (generous, greedy, scrooge), VAD, CNG
- Support distribution algorithm
- Access Layer
- Access Layer Security: Intrudent detecion, Brute Force Prevention, Antiflooding
- Multiple domain - default domain
- Socket indicator
- Firewall Whitelist/Blacklist
- Document update

### Changed
- ansible role convention
- no remove verbose log input data
- replace local var by NgVars
- use pubsub instead of queue
- from host with hostname after fresh restart

### Fixed
- Fix unintended field for gateways update
- Fix nft empty ruleset

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
