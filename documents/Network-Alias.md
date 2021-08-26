<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

Since the LibreSBC was designed for distributed system, the network configuration for member have to map address and member nodeid to resolving.  

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/base/netalias-BLUE?style=for-the-badge&logo=Safari">

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of profile (unique)    
desc         |`string` | Description 
addresses |`list` |Map of address and node id.

### Addresses Map
Parameter    | Category           | Description                     
:---         |:---                |:---                             
member       |`string` `required` |NodeID of member in cluster
listen       |`string` `required`| The listening ip address 
advertise |`string` `required`| The advertising ip address


