#!/bin/sh

vconfig add eth0 10
ip link set eth0.10 up
ip addr add 192.168.2.1/24 dev eth0.10
ip addr add 2001:470:e4dd:2::1/64 dev eth0.10
sysctl -w net.ipv4.conf.eth0.forwarding=1
sysctl -w net.ipv4.conf.eth0/10.forwarding=1
sysctl -w net.ipv6.conf.all.forwarding=1
sysctl -w net.ipv6.conf.eth0.accept_ra=2

ip route add local 0.0.0.0/0 dev lo table 100
ip rule add fwmark 2 lookup 100

ip -6 route add local ::/0 dev lo table 100
ip -6 rule add fwmark 2 lookup 100

/etc/init.d/isc-dhcp-server start
/etc/init.d/radvd start
