<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

LibreSBC provide Manipulation Class, giving LibreSBC operator the ability to control session in term of signalling, media and management as well, The Manipulation is powerful function and it's risk if you not use them properly. Variances among SIP networks, such as incompatible interconnection can disrupt SIP operations. Manipulation concentrate on the function of
* SIP traffic by manipulating SIP messages. 
* Modify/Add/Remove session-variables and ng-variables

The function might effect directly to session or provide `fine-grained` variable for other class function.

Basically, there are 3 main parts of one manipulation rule:
* condition: condition set of criteria to decide what part will do next, just image it is like `IF` statement.
* action: sequence of action will be process if condition is match
* antiaction: sequence of action will be process if condition is not match

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/class/manipulation-BLUE?style=for-the-badge&logo=Safari">

Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name class    
desc       |`string`| description for class
condition  |`map`  | combine the logic and list of checking rules
actions     |`list` `required` | list of action map when conditions is true
antiactions |`list`  | list of action when conditions is false

### Condition
Parameter  | Category           | Description                     
:---       |:---                |:---    
logic |`enum`|`AND` <br>`OR` bolean operator for rule entries
rules |`list`|list of rule map

#### Rule Map

Parameter  | Category           | Description                     
:---       |:---                |:---  
refervar |`string` | variable name
pattern |`string` |variable pattern with regex

### Action/AntiAction Map
Parameter  | Category           | Description                     
:---       |:---                |:---  
action |`enum` | `set` `log` `hangup` `sleep`
refervar |`string` |name of reference variable
pattern |`string` |variable pattern with regex
targetvar|`string`|name of target variable
values |`list`| value of target variable


