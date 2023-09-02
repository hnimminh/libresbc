<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

There are multiple methods to install LibreSBC, but using Ansible is the best choice for convenient and minimize workload. If Ansible is new for you let spend a bit effort to learn it. If you already used Ansible then go head.

<p align="center"> <img width="800" src="https://user-images.githubusercontent.com/58973699/130829862-94ae80a8-f90d-426b-9d7c-efb9f5ec56f8.png"></p>

## Requirements
* LibreSBC Machine: Debian 10 buster.
* Ansible Machine: MacOS/Linux with Ansible ( [Ansible Installation Guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html))
    * rsync is required on Ansible host.
    * version of Ansible is not important (2.9.14 is used in the test)

## Get starts

### 1. Download the LibreSBC repository source code.
```bash
git clone --depth 1 --branch <tag_name> https://github.com/hnimminh/libresbc.git
```
### 2. Move to deployment directory
```
cd libresbc/build/ansible
```
### 3. Update Ansible Config, and fill below line:
```
vi ansible.cfg
```

```ansible
[defaults]
private_key_file    = <ssh-private-key-to-access-libresbc>
remote_port         = <ssh-port-of-libresbc-host-default-is-22>
remote_user         = <ssh-username-to-access-libresbc-host>
vault_password_file = <ansible-vault-secret-file>
```
### 4. Declare your LibreSBC into Inventory
```
vi inventories/production/hosts.yml
```

```yaml
sbcs:
  hosts:
    <machine-name>:
      ansible_host: <libresbc-machine-ip>
      nodeid: <unique-nodeid>
```
* `ansible_host`: ip address of libresbc that ansible machine can ssh to
* `nodeid`: must be unique name, best practice is using Greek/Japan/Roma God's name or whatever.. as long as they unique and related. `nodeid` and `machine-name` can be same.

### 5. Deployment
```bash
ansible-playbook playbooks/deployment.yml -i inventories/production -l "<machine-name>" -t "platform,libre,nginx,captagent" -e "debian_codename=bullseye" -e "signalwire_pat_token=Your-SignalWire-Personal-Access-Tokens"
```

#### Note:
* Since 2022, [SignalWire Personal Access Tokens (PAT)s](https://freeswitch.org/confluence/display/FREESWITCH/HOWTO+Create+a+SignalWire+Personal+Access+Token) are required to access FreeSWITCH install packages
* Once you registered and got _**SignalWire Personal Access Tokens**_, you will need to declare ansible extra variable to install FreeSWITCH (when you run ansible-playbook with tag _platform_ or _freeswitch_)
* Example:
```bash
ansible-playbook playbooks/deployment.yml -i inventories/production -l "<machine-name>" -t "platform,libre,nginx,captagent" -e "signalwire_pat_token=Your-SignalWire-Personal-Access-Tokens"
```
<br>

#### Specify Debian version (`bullsyes` & `buster`)
* when `debian_codename` is omitted `buster` will be used as default [22/08/2023]
```bash
ansible-playbook playbooks/deployment.yml -i inventories/production -l "<machine-name>" -t "platform,libre,nginx,captagent" -e "debian_codename=bullseye"
```

*..and enjoy* 👏

## Troubleshooting
*This will be collected from issue that encountered in community*

<br><br>
## Note

* There is other method like bash script, docker are not recommended if you not familiar with LibreSBC.


