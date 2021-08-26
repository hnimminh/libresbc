<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

The translation rules replace a sub string of the input number if the number matches the match pattern. The regex [prce](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) engine is used to check for a match based on the match pattern.

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/class/translation-BLUE?style=for-the-badge&logo=Safari">
 
Parameter  | Category           | Description                     
:---       |:---                |:---                             
name       |`string` `required` | The name class    
desc       |`string`| description for class
caller_number_pattern        |`string` `required` | caller number pattern use pcre, empty string mean `don't care`
destination_number_pattern   |`string` `required` | destination number pattern use pcre, empty string mean `don't care`
caller_number_replacement   |`string` `required` | replacement that refer to caller number pattern use pcre
destination_number_replacement   |`string` `required` | replacement that refer to destination number pattern use pcre
caller_name   |`string`  | `_auto` (default): use the caller id name in leg-in and passed to legout <br> `_caller_number`: use caller id number as name <br> or any string for fixed value

## PRCE Overview
Below table show most formalisms provide the following operations to construct regular expressions.
Char  | Description  | Example | Match | MisMatch              
:---  |:---          |:---     |:---   |:---  
^ |The start of a line. |^firm |firming |confirm
$ |The end of the line. |firm$ |confirm |firming
\ |Escape the special character.
. |Match any chars except new line |libre.bc |libresbc |librebc
? |Zero or one quantifier |li?re|lire, libre |libbre
`+` |One or more quantifier |lib+re| libre, libbre|lire
`*` |Zero or more quantifier|lib*re| libre, libbre, lire|lidre
\| |Alternation | libre\|sbc | sbc, libre | libresbc
[] |Match a single chars in a class |12[345]a |123a, 124a |12a, 126a
[^]|Not match a single chars in a class |12[^345]a |126a, 121a |123a, 124a
[-] |Range of match chars in a class |libre[1-6] |libre2, libre1, libre6 |libre0, libre7
{n} |n times exactly | libre{2}sbc |libreesbc|librsbc, libreeesbc
{n,m} |from n to m times |libre{1-2}sbc |libreesbc, libresbc|librsbc, libreeesbc
() |Sub-pattern or reference group
%{n}|Back reference to group in pattern

## Example:

* Strip 0 and Add country code +84 for Vietnam Mobile number
  * pattern: ^0(9[0-9]{8})$
  * replacement: +84%{1}

  * Translations:  
    * 09012345678 → +849012345678
    * 12345678 → 12345678 (no change)


* Singapore Number call Vietnam Number then, remove country of Singpore and append 84 prefix, for Vietnam Number just remove country code
```json
    "caller_number_pattern": "^+?65([0-9]{8})$",
    "destination_number_pattern": "^+?84([0-9]+)$",
    "caller_number_replacement": "84%{1}",
    "destination_number_replacement": "%{}",
    "caller_name": "_auto",
```

  * Translations:  
    * 6531245678:+849012345678  → 8431245678:9012345678
    * 8131245678 → +8431245678 (no change)
