#!/bin/bash

# IPs to allow through proxy. Probably need to change from the defaults!
ALLOWED_IPADDRS=('155.98.32.70')

# Addresses to NAT (public,private). Add public IP NAT mappings here.
NAT_ADDRS=()

#
# Grab interface info. Proxy internal IP needs to match address below!
#
CIF=`cat /var/emulab/boot/controlif`
IF1=`/usr/local/etc/emulab/findif -i 192.168.1.10`

if [ -z $IF1 ]
then
	echo "Could not find interface for running dhcpd!"
	exit 1
fi

#
# Enable NAT and firewall setup
#

# Forwarding firewall rules.  Allow established connections, and new
# connections on specific ports (e.g. SSH port 22). Allow out all
# traffic from the internal network.
#sudo iptables -F FORWARD
#sudo iptables -P FORWARD DROP
#for ipa in ${ALLOWED_IPADDRS[@]}; do
#    sudo iptables -A FORWARD -i $CIF -o $IF1 -s $ipa -j ACCEPT
#    sudo iptables -A FORWARD -i $IF1 -o $CIF -d $ipa -j ACCEPT
#done
#sudo iptables -A FORWARD -i $CIF -o $IF1 -s 155.98.32.70 -p udp --sport 53 -j ACCEPT
#sudo iptables -A FORWARD -i $IF1 -o $CIF -d 155.98.32.70 -p udp --dport 53 -j ACCEPT
#sudo iptables -A FORWARD -i $CIF -o $IF1 -s 155.98.33.74 -p udp --sport 123 -j ACCEPT
#sudo iptables -A FORWARD -i $IF1 -o $CIF -d 155.98.33.74 -p udp --dport 123 -j ACCEPT

# Proxy ARP entries for the two 1-to-1 NAT addresses
# ! This never worked right, so IP aliases are used instead.
#sudo arp -i $CIF -Ds 155.98.36.197 $CIF pub
#sudo arp -i $CIF -Ds 155.98.36.198 $CIF pub

# Iterate over and set up 1-to-1 NAT pairs
#sudo iptables -t nat -F
#for apair in ${NAT_ADDRS[@]}; do
#    tmparr=(${apair//,/ })
#    pubaddr=${tmparr[0]}
#    privaddr=${tmparr[1]}

    # Add IP alias for the public address
#    sudo ip addr add $pubaddr dev $CIF

    # Set up 1-to-1 NAT for the device.
#    sudo iptables -t nat -A POSTROUTING -o $CIF -s $privaddr -j SNAT --to-source $pubaddr
#    sudo iptables -t nat -A PREROUTING -i $CIF -d $pubaddr -j DNAT --to-destination $privaddr
#done

# Tell kernel to forward packets
#sudo sysctl -w net.ipv4.ip_forward=1

#
# Set up the DHCP server
#
sudo apt-get -q update && \
    sudo apt-get -q -y install --reinstall isc-dhcp-server || \
    { echo "Failed to install ISC DHCP server!" && exit 1; }

sudo cp -f /local/repository/etc/dhcpd.conf /etc/dhcp/dhcpd.conf || \
    { echo "Could not copy dhcp config file into place!" && exit 1; }

sudo ed /etc/default/isc-dhcp-server << SNIP
/^INTERFACES/c
INTERFACES="$IF1"
.
w
SNIP

if [ $? -ne 0 ]
then
    echo "Failed to edit dhcp defaults file!"
    exit 1
fi

if [ ! -e /etc/init/isc-dhcp-server6.override ]
then
    sudo bash -c 'echo "manual" > /etc/init/isc-dhcp-server6.override'
fi

sudo service isc-dhcp-server start || \
    { echo "Failed to start ISC dhcpd!" && exit 1; }

sudo apt-get -y install --no-install-recommends iperf3

exit $?
