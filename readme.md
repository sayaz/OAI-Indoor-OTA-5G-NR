# 5G-NR & Wi-Fi Coexistence Experiment (5 GHz band) Indoor OTA Lab

This profile instantiates an experiment for testing OAI 5G with SDR based UEs in
standalone mode using resources in the POWDER indoor over-the-air (OTA) lab.
The indoor OTA lab includes:

You can find a diagram of the lab layout here: [OTA Lab
Diagram](https://gitlab.flux.utah.edu/powderrenewpublic/powder-deployment/-/raw/master/diagrams/ota-lab.png)

The following will be deployed:

- A d740 compute node as 5G-CN.
- 3 x USRP-B210 as UE.
- 1 x USRP-B210 OTA as gNB.
- NUC compute nodes for UE and gNB.
- A Wi-Fi AP connected with a compute node.
- A Wi-Fi Client connected to Wi-Fi AP (WLAN).

![Screenshot 2024-08-29 at 6 03 15 PM](https://github.com/user-attachments/assets/81e08335-38ef-4ccd-8427-dc1daf907947)

After all startup scripts have finished...

## Core Network ##

Start the 5G core network services. It will take several seconds for the services to start up. Make sure the script indicates that the services are healthy before moving on.

```
cd /var/tmp/oai-cn5g-fed/docker-compose
sudo python3 ./core-network.py --type start-mini --scenario 1
```

In another session, start following the logs for the AMF. This way you can see when the UE/gNB syncs with the network.

```
sudo docker logs -f oai-amf
```

## gNB ##

If you need to change the frequency parameters of gNB, open file `/var/tmp/etc/oai/gnb.sa.band46.fr1.106PRB.usrpx310.conf` and edit the following parameters:
```
absoluteFrequencySSB  = 783648;
dl_frequencyBand      = 46;
dl_absoluteFrequencyPointA = 782376;
ul_frequencyBand = 46;
```

You also need to edit file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},`

Once completed, you need to build/compile:

```
/var/tmp/oairan/cmake_targets/build_oai -w USRP --build-lib nrscope --gNB --ninja
```

**Start the gNB** :

For ```PRB = 106```, ```SCS = 30 KHz``` and ```band = n46```:
```
sudo numactl --membind=0 --cpubind=0 /var/tmp/oairan/cmake_targets/ran_build/build/nr-softmodem -E  -O /var/tmp/etc/oai/gnb.sa.band46.fr1.106PRB.usrpx310.conf --gNBs.[0].min_rxtxtime 6 --sa --MACRLCs.[0].dl_max_mcs 28 --tune-offset 23040000
```

## UE ##

Similarly to make changes in the frequency edit the file `/var/tmp/oairan/common/utils/nr/nr_common.c` insert an additional line between `87 and 89` with `{46,  5150000, 5925000, 5150000, 5925000,  1, 743333,  15},` and build

```
/var/tmp/oairan/cmake_targets/build_oai -w USRP --nrUE --ninja 
```

**Start the UE**:

For ```PRB = 106```, ```SCS = 30 KHz``` and ```band = n46```:
```
sudo numactl --membind=0 --cpubind=0   /var/tmp/oairan/cmake_targets/ran_build/build/nr-uesoftmodem -E -O /var/tmp/etc/oai/ue.conf  -r 106  -C 5754720000  --usrp-args "clock_source=internal,type=b200"  --band 46  --numerology 1  --ue-fo-compensation  --ue-txgain 0   --ue-rxgain 120   --nokrnmod   --dlsch-parallel 4   --sa --tune-offset 23040000
```

> [!NOTE]
> Sometimes if the Tx/Rx power gain is low, the UE may receive a low power from gNMB and may not start with the arguments provided, in that case, try different gain values.

> It is also found that UE does not attach to the CN on first try. In such case restart both gNB and UE.

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

## Additional commands for debuggin ##
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


**Start trace on CN**

```sudo tcpdump -i demo-oai   -f "not arp and not port 53 and not host archive.ubuntu.com and not host security.ubuntu.com" -w /users/sayazm/5G_5Gz_Testing.pcap```


**iperf test (Client (UE) to CN)**

CN : `sudo docker exec -it oai-ext-dn iperf3 -s`
UE : `iperf3 -c 192.168.70.135 -t 10`


**iperf test (CN to UE (DL))**

First find IP address of UE : ifconfig oaitun_ue1

CN : `sudo docker exec -it oai-ext-dn iperf3 -c 12.1.1.151`
UE : `iperf3 -s`


## How to take MAC layer Wireshark trace ##

Simply call ```build_oai``` the usual way, for example ```./build_oai --eNB -w USRP```. The T tracer is compiled in by default.

**Tracer Side**
Go to the directory ```common/utils/T/tracer``` and do ```make```. This will locally compile all tracer executables, and place them in ```common/utils/T/tracer```. 

In case of failure with one of the following errors:
```/usr/bin/ld: cannot find -lXft```

Run
```sudo apt-get install libxft-dev```

**Run the UE**
Run the ue-softmodem with the option ```--T_stdout 2``` and it will wait for a tracer to connect to it before processing.
```
cd cmake_targets/ran_build/build
sudo ./lte-softmodem -O [configuration file] --T_stdout 2
```

**Then Run Live usage**
Launch wireshark and listen on the local interface (lo). Set the filter to ```udp.port==9999``` and read below for configuration.

Browse to ```/var/tmp/oairan/common/utils/T/tracer/``` and run
```
./macpdu2wireshark -d /var/tmp/oairan/common/utils/T/T_messages.txt -live
```


### Configure Wireshark for 5G-NR ###
Use a recent version of wireshark. The steps below were done using version 3.3.2. Maybe some options are different for your version of wireshark. Adapt as necessary.

In the menu, choose ```Edit->Preferences```. In the preference window, unroll ```Protocols```.

Go to ```MAC-NR```. Select both options (```Attempt to decode BCCH```, ```PCCH and CCCH data using NR RRC dissector``` and ```Attempt to dissect LCID 1-3 as srb1-3```).

For Source of ```LCID -> drb channel settings``` choose option From ```static table```. Then click the Edit... button of ```LCID -> DRB Mappings Table```. In the new window, click on +. Choose LCID 4, DRBID 1, UL RLC Bearer Type AM, SN Len=18, same thing for DL RLC Bearer Type. Then click OK.

Now, go to ```RLC-NR```. Select ```Call PDCP dissector for SRB PDUs```. For ```Call PDCP dissector for UL DRB PDUs``` choose ```18-bit SN```. Same for DL. Select ```Call RRC dissector for CCCH PDUs```. You don't need to select May see RLC headers only and Try to reassemble UM frames.

Now, go to ```PDCP-NR```. Select what you want in there. It's good to select ```Show uncompressed User-Plane data as IP```. Also good to select ```Show unciphered Signalling-Plane data as RRC```. For ```Do sequence number analysis``` it can be good to use ```Only-RLC-frames``` but anything will do. We don't use ROHC so you don't need to select Attempt to decode ROHC data. And the layer info to show depends on what you want to analyse. ```Traffic Info``` is a good choice. You are done with the preferences. You can click OK.

Then, in the menu ```Analyze```, choose ```Enabled Protocols```.... In the new window search for ```nr``` and ```select mac_nr_udp``` to have ```MAC-NR over UDP```. And that's it. Maybe other settings can be changed, but those steps should be
enough for a start.

