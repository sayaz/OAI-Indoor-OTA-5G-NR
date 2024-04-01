## OAI 5G using the POWDER Indoor OTA Lab

This profile instantiates an experiment for testing OAI 5G with SDR based UEs in
standalone mode using resources in the POWDER indoor over-the-air (OTA) lab.
The indoor OTA lab includes:

- 4x NI X310 SDRs, each with a UBX-160 daughter card occupying channel 0. The
  TX/RX and RX2 ports on this channel are connected to broadband antennas. The
  SDRs are connected via fiber to near-edge compute resources.

You can find a diagram of the lab layout here: [OTA Lab
Diagram](https://gitlab.flux.utah.edu/powderrenewpublic/powder-deployment/-/raw/master/diagrams/ota-lab.png)

The following will be deployed:

- A d430 compute node to host the core network
- A d740 compute node for the gNodeB
- One of the four indoor OTA X310s
- One of the four indoor OTA B210 as UE
- NUC compute node for UE

After all startup scripts have finished...

**Core Network**

Start the 5G core network services. It will take several
seconds for the services to start up. Make sure the script indicates that the
services are healthy before moving on.

```
cd /var/tmp/oai-cn5g-fed/docker-compose
sudo python3 ./core-network.py --type start-mini --scenario 1
```

In yet another session, start following the logs for the AMF. This way you can
see when the UE syncs with the network.

```
sudo docker logs -f oai-amf
```

**gNB**

If you need to change the frequency parameters of gNB, open file `/var/tmp/etc/oai/gnb.sa.band78.fr1.106PRB.usrpx310.conf` and edit line `48`, `49`, `51` and `71`.

You also need to edit file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},`

Once completed, you need to build/compile:

```
/var/tmp/oairan/cmake_targets/build_oai -I --ninja

/var/tmp/oairan/cmake_targets/build_oai -w USRP --build-lib nrscope --gNB --ninja
```

Now start the gNB:

```
sudo numactl --membind=0 --cpubind=0   /var/tmp/oairan/cmake_targets/ran_build/build/nr-softmodem -E  -O /var/tmp/etc/oai/gnb.sa.band46.fr1.106PRB.usrpx310.conf --gNBs.[0].min_rxtxtime 6 --sa --MACRLCs.[0].dl_max_mcs 28 --tune-offset 23040000
```

**UE**

Similarly if you want to make any change in the frequency edit the file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},` and build

```
/var/tmp/oairan/cmake_targets/build_oai -I --ninja

/var/tmp/oairan/cmake_targets/build_oai -w USRP --nrUE --ninja 
```

Start UE:

```
sudo numactl --membind=0 --cpubind=0   /var/tmp/oairan/cmake_targets/ran_build/build/nr-uesoftmodem -E   -O /var/tmp/etc/oai/ue.conf   -r 106   -C 5754720000  --usrp-args "clock_source=internal,type=b200"  --band 46  --numerology 1  --ue-fo-compensation  --ue-txgain 0   --ue-rxgain 120   --nokrnmod   --dlsch-parallel 4   --sa
```

**After the UE associates, open another session check the UE IP address.**

Check UE IP address
```
ifconfig oaitun_ue1
```
Add a route toward the CN traffic gen node
```
sudo ip route add 192.168.70.0/24 dev oaitun_ue1
```

You should now be able to generate traffic in either direction:

```
# from UE to CN traffic gen node (in session on ue node)
ping 192.168.70.135

# from CN traffic generation service to UE (in session on cn node)
sudo docker exec -it oai-ext-dn ping <UE IP address>
```

**Additional commands for debuggin**
- If you want to see the spectrum you can use any of the below commands. Press `l` to decrease the reference level:
```
/usr/lib/uhd/examples/rx_ascii_art_dft --freq 5754.72e6 --rate 40e6 --gain 80 --frame-rate 70 --bw 50e6
```

For GUI (you need X11 forwarding activated)
```
/usr/bin/uhd_fft -f 5754.72e6 -s 40e6 -g 76
```
If error exist related to platform plugin, exit and
```
export DISPLAY=:0
ssh -X sayazm@ota-nuc1.emulab.net
```


Start trace on CN

```sudo tcpdump -i demo-oai   -f "not arp and not port 53 and not host archive.ubuntu.com and not host security.ubuntu.com" -w /users/sayazm/5G_5Gz_Testing.pcap```


iperf test (Client (UE) to CN)

CN : `sudo docker exec -it oai-ext-dn iperf3 -s`
UE : `iperf3 -c 192.168.70.135 -t 10`


iperf test (CN to UE (DL))

First find IP address of UE : ifconfig oaitun_ue1

CN : `sudo docker exec -it oai-ext-dn iperf3 -c 12.1.1.151`
UE : `iperf3 -s`


**How to take MAC layer Wireshark trace**

Simply call ```build_oai``` the usual way, for example ```./build_oai --eNB -w USRP```. The T tracer is compiled in by default.

**Tracer Side**
Go to the directory ```common/utils/T/tracer``` and do ```make```. This will locally compile all tracer executables, and place them in ```common/utils/T/tracer```. 

In case of failure with one of the following errors:
```/usr/bin/ld: cannot find -lXft```

Run
```sudo apt-get install libxft-dev```

