<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Overview
LibreSBC provided a powerful built-in routing engine which allows to selects an destination entities (outbound interconnection) for an inbound call based on one/multiple session criteria/variable. The Routing Engine can serve for most of use case in real life include:

* Inbound Classify
* Block Traffic
* Jumping routing plan
* Diversity routing criteria with engine variable
* Various Matching type: Longest matching prefix, Exactly match, Comparing 
* Load Distribution: Fail-over, Load Balancing, Percentage Load
* Flexible by Manipulate/Translation
 

## Routing Table
<img src="https://img.shields.io/badge/API-/libreapi/routing/table-BLUE?style=for-the-badge&logo=Safari">

Routing table is key element of data for routing engine, It define the fundamental schema of routing. It must be assigned to an inbound interconnection to take effect and can be reuse many time if needed. These following parameters can be declare in routing table: 

Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name of routing table    
action     |`enum` `required`| The action for routing, include `route`, `block`, `query`. Default is `query` <br/> `route` go directly to destination interconnection that defined in routes map object. <br/> `block` block traffic <br/>`query` do the query route via routing records with variable criteria.
variable   |`string` | The name of engine variable that will be configure value in routing record. Applicable only action is `query`. 
routes     |`map` | Route Map Object. Applicable only action is `route`.


## Routing Record
<img src="https://img.shields.io/badge/API-/libreapi/routing/record-BLUE?style=for-the-badge&logo=Safari">

Routing Record is unit element of data for routing engine, It define the way how engine examine the rule to select the next destination. Routing record has various matching type, and action as well as value to support engine select property next-hop. These following parameters can be declare in routing record:

Parameter  | Category           | Description                     
:---       |:---                |:---                             
table       |`string` `required` | The routing table name  the routing record belong to 
match       |`enum` `required` | The matching type that will be define criteria to select. <br/>{`eq`, `ne`, `gt`, `lt`}: compare matching <br/>`em`: exactly match <br/>`lpm`: longest prefix matching
value |`string` `required` |The value can be present by two purpose:<br/>→ The fixed value of variable that already defined in routing table (`lpm` `em`) <br/>→ Name of other variable for compare (`eq`, `ne`, `gt`, `lt`) <br/>💢**DEFAULT_ENTRY** is value alias for default records, its similar to default route (0.0.0.0/0) in network routing table.
action     |`enum` `required`| The action for routing, include `route`, `block`, `jumps`. Default is `query` <br/> `route` go directly to destination interconnection that defined in routes map object. <br/> `block` block traffic <br/>`jumps` jumps to another routing table
routes     |`map` | Route Map Object. Applicable only action is `route`.

**Comparing matching Note**
* eq: equal to
* ne: not equal
* gt: greater than
* lt: less than


### Routes Map Object
The `routes` may be used by both table (applicable with `route`) and record (applicable with `jumps` & `route`), it is quite simple but flexible enough for load sharing and refer to use another routing schema in particular condition.
Parameter    | Category           | Description                     
:---         |:---                |:---                             
primary         |`string` `required` |`outbound interconnection` `routing-table` <br/>The primary route
secondary       |`string` `required` |`outbound interconnection` `routing-table` <br/>The secondary route                     
load   |`int` `required` | `0-100` <br/>Distributed value of load sharing between primary and secondary. eg:<br/> `load=100` mean 100% call will use primary as route, only failover to secondary if primary is down. <br/>`load=50` mean load balancing between primary and secondary.

## Example:
Suppose that We have:
* Three telcos Orange, Docomo and VNPT connect to LibreSBC as outbound interconnections
* The Core-Component (your PBX, Contact Center, etc)

And here is requirement:
1. Outbound call from Core-Component to France (+33) will use Orange, if Orange failure fail-over to Docomo
2. Outbound call from Core-Component to Japan (+81) will use Orange and Docomo load balancing
3. The rest of Outbound call from Core-Component will use VNPT.

### Solution:

**routing table**
```json
{
  "name": "default",
  "desc": "example routing",
  "variables": [
    "dstnumber"
  ],
  "action": "query"
}
```

**routing record**
```json
{
    "table": "default",
    "match": "lpm",
    "value": "+44",
    "action": "route",
    "routes": 
    {
        "primary": "Orange",
        "secondary": "Docomo",
        "load": 100
    }
}

{
    "table": "default",
    "match": "lpm",
    "value": "+81",
    "action": "route",
    "routes": 
    {
        "primary": "Docomo",
        "secondary": "Orange",
        "load": 50
    }
}

{
    "table": "default",
    "match": "lpm",
    "value": "DEFAULT_ENTRY",
    "action": "route",
    "routes": 
    {
        "primary": "VNPT",
        "secondary": "VNPT",
        "load": 50
    }
}
```

