#!/bin/bash

reload(){
  basedir="{{rundir}}/platform/netfilter"

  /usr/sbin/ipset restore < "$basedir/rtpset"
  echo "Restored $basedir/rtpset"

  /usr/sbin/ipset restore < "$basedir/sipset"
  echo "Restored $basedir/sipset"

  /sbin/iptables-restore $basedir/rules
  echo "Restored $basedir/rules"
}


clear(){
  /sbin/iptables -P INPUT ACCEPT
  /sbin/iptables -P FORWARD ACCEPT
  /sbin/iptables -P OUTPUT ACCEPT
  /sbin/iptables -t nat -F
  /sbin/iptables -t mangle -F
  /sbin/iptables -F
  /sbin/iptables -X
  /usr/sbin/ipset flush
  echo "NetFilter [iptable & ipset] was cleared"
  /sbin/iptables -nvL
  echo "-----------------------------------------------------------------------------------------------------"
  /usr/sbin/ipset list
}

show(){
  /sbin/iptables -nvL
  echo "-----------------------------------------------------------------------------------------------------"
  /usr/sbin/ipset list
}

dump(){
  /sbin/iptables-save > iptables.netfilter
  /usr/sbin/ipset save > ipset.netfilter
  echo "NetFilter (iptables.netfilter & ipset.netfilter) files was dumped in current directory"
}

case "$1" in
    reload)
        reload
        ;;
    reset)
        reset
        ;;
    clear)
        clear
        ;;
    show)
        show
        ;;
    dump)
        dump
        ;;
    *)
        echo "Usage: netfilter {reload|reset|dump|show|clean}"
        ;;
esac
