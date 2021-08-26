<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

The Media class define the behaviors of interconnection for media stream and related signalling, include:
* Media Codecs
* Codec Negotiation Method
* Media Mode
* DTMF (Dual-tone multi-frequency signaling) 
* and others like: comfort noise or voice active detect, etc.


## Setting
<img src="https://img.shields.io/badge/API-/libreapi/class/media-BLUE?style=for-the-badge&logo=Safari">
 
Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name class
desc       |`string`| description for class
codecs     |`enum` `list` `required` | The ordered list of codecs for media offer. <br> `PCMA` `PCMU` `OPUS` `G729` `AMR` `AMR-WB` 
codec_negotiation |`enum` | codec negotiation mode <br>`generous`: refer remote,<br>`greedy`: refer local,<br>`scrooge`: enforce local
media_mode |`enum`|media processing mode. <br>`transcode`: media will be process and transcoding if need. <br>`proxy`: media go through but not touch.<br>`bypass`: direct between endpoint, libresbc not involve to.
dtmf_mode |`enum`| Dual-tone multi-frequency mode.<br>`rfc2833` `info` `none`
cng|`bool`|comfort noise generate
vad|`bool`|voice active detection, no transmit data when no party speaking

