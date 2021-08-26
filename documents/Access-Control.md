<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

An access control (ACL) is a list of permissions/rules associated with an object where the list defines what network entities are allowed to access the object. By right you shouldn't need to visit here. ACL will be auto configuration whenever configuration change on interconnection or network change. If you need touch on ALC, seem like your network is designed improperly.

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/base/acl-BLUE?style=for-the-badge&logo=Safari">

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of profile (unique)    
desc         |`string` | Description 
action |`enum` |default action for all rules `allow` `deny`
rules |`list` | list of rule

Parameter    | Category           | Description                     
:---         |:---                |:---                              
action |`enum` |`allow` `deny`
key |`enum` | `cidr` `domain`
value|`cidr` `domain` |acl rule value depend on type

### Builtin ACL
Name  | Description                     
:---  |:--- 
rfc1918.auto	|RFC 1918 Space
nat.auto	|RFC 1918, excluding your local LAN
loopback.auto	|ACL for your loopback LAN
localnet.auto	|ACL for your local LAN 
