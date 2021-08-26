<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

The Capacity class define limit of how much traffic can pass, include 
* **Call per second**(`cps`), exactly it measure of how many calls are being setup and torn down per last 1000ms, the limiting factor is the ability to process the SIP messages.
* **Concurrent call**, It is less a limit of SIP but rather the RTP media streaming. This can further be broken down to available bandwidth and the packets per second. The theoretical limit on concurrent calls through a gigabit Ethernet port would be around 10,500 calls without RTCP, assuming G.711 codec and the link-level overheads. Theory is great at all, but in reality the kernel networking layer will be your limiting factor due to the packets per second of the RTP media stream and other factors.


## Setting
<img src="https://img.shields.io/badge/API-/libreapi/class/capacity-BLUE?style=for-the-badge&logo=Safari">
 
Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name class    
desc       |`string`| description for class
cps        |`int` `required` | call per second 
concurentcalls     |`int` `required` | concurrent call
