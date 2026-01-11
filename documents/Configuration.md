<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Work Flow
LibreSBC is completed solution with modular design of Session Border Controller. The design allows LibreSBC to be extended and adapted flexibly real life functions without requiring massive efforts. Before diving into detailed configuration, this page will outline all mandatory configuration steps in order to properly configure LibreSBC. The following graph show the work flow for system configuration. 

<br/><br/>
<p align="center"> <img width="900" src="https://user-images.githubusercontent.com/58973699/126864932-85807ca6-2ea7-4d5e-86b4-c1750112b54a.png"></p>

## Tips

Here is some question that might help you design you solution with LibreSBC.
* What is your network topology?
* Identify IP networking scenario for SBC
  * Connect among network segment?
  * SBC function type: is this Access, Interconnection, Enterprise or combined?

## Agenda

* [[SIP Profile]]: SIP Signalling and RTP Media Network
* [[Interconnection]]
  * [[Inbound]]: Inbound Traffic Connection
  * [[Outbound]]: Outbound Traffic Connection
  * [[Gateway]]: Inbound Traffic Connection
* Class: Service Class
  * [[Media]]: Media Service include: Transcoding, Codec selection, media proxy ..
  * [[PreAnswer (Early Media)]]: Ringtone, Announcement ..
  * [[Translation Rules]]: Party Number translation: callerid number, callerid name, destination number
  * [[Capacity]]: rate limit, concurrent call, call per second, traffic shaping
  * [[Manipulation]]: SIP header normalize and manipulation. engine variable modify ..
* Base
  * [[Access Control]]: Network define function
  * [[Network Alias]]: Network Address declaration
* [[Cluster]]: Cluster Configuration ..
* [[Routing]]

## Rest API
Once LibreSBC had been installed successfully, you can access to online Rest API via:

`https://<your-libresbc-ip>:8443/apidocs`

<br/>
 