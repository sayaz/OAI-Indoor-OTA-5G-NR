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

On `cn`:

If you'd like to monitor traffic between the various network functions and the
gNodeB, start tshark in a session:

```
sudo tshark -i demo-oai -f "not arp and not port 53 and not host archive.ubuntu.com and not host security.ubuntu.com"
```

In another session, start the 5G core network services. It will take several
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

If you need to change the frequency parameters of gNB, open file `/var/tmp/etc/oai/gnb.sa.band78.fr1.106PRB.usrpx310.conf` and edit line `48`, `49`, `51` and `71`.

You also need to edit file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},`

Once completed, you need to build/compile:

```
/var/tmp/oairan/cmake_targets/build_oai -I --ninja

/var/tmp/oairan/cmake_targets/build_oai -w USRP --build-lib nrscope --gNB --ninja
```

Now start `gNB`:

```
sudo numactl --membind=0 --cpubind=0 /var/tmp/oairan/cmake_targets/ran_build/build/nr-softmodem -E -O /var/tmp/etc/oai/gnb.sa.band78.fr1.106PRB.usrpx310.conf --sa --MACRLCs.[0].dl_max_mcs 28 --tune-offset 23040000
```

On `ue`:

Similarly if you want to make any change in the frequency edit the file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},` and build

```
/var/tmp/oairan/cmake_targets/build_oai -I --ninja

/var/tmp/oairan/cmake_targets/build_oai -w USRP --nrUE --ninja 
```


After you've started the gNodeB, start the UE:

```
sudo numactl --membind=0 --cpubind=0 /var/tmp/oairan/cmake_targets/ran_build/build/nr-uesoftmodem -E -O /var/tmp/etc/oai/ue.conf -r 106 -C 5754720000 --band 46 --numerology 1 --ue-txgain 0 --ue-rxgain 114 --nokrnmod --dlsch-parallel 4 --sa
```

After the UE associates, open another session check the UE IP address.

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


Known Issues and Workarounds:

- The oai-amf may not list all registered UEs in the assoicated log.
- The gNodeB soft modem may spam warnings/errors about missed DCI or ULSCH
  detections. It may crash unexpectedly.
- Exiting the gNodeB soft modem with ctrl-c will often leave the SDR in a funny
  state, so that the next time you start it, it may crash with a UHD error. If
  this happens, simply start it again.
- The module may not attach to the network or pick up an IP address on the first
  try. If so, put the module into airplane mode with `sudo sh -c "chat -t 1 -sv ''
  AT OK 'AT+CFUN=4' OK < /dev/ttyUSB2 > /dev/ttyUSB2"`, kill and restart
  quectel-CM, then bring the module back online. If the module still fails to
  associate and/or pick up an IP, try putting the module into airplane mode,
  rebooting the associated NUC, and bringing the module back online again.
- `chat` may return an error sometimes. If so, just run the command again.

"""


