#!/usr/bin/env python

import os

import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.igext as IG
import geni.rspec.emulab.pnext as PN
import geni.rspec.emulab.spectrum as spectrum


tourDescription = """
# OAI 5G using the POWDER Indoor OTA Lab 

This profile instantiates an experiment for testing OAI 5G with SDR based UEs in
standalone (SA) mode using resources in the POWDER indoor over-the-air (OTA) lab.
The indoor OTA lab includes:

You can find a diagram of the lab layout here: [OTA Lab
Diagram](https://gitlab.flux.utah.edu/powderrenewpublic/powder-deployment/-/raw/master/diagrams/ota-lab.png)

The following will be deployed:

- Two d430 compute node for CN and Wi-Fi AP Mgt.
- Two NUC compute node for UE and gNB
- 1xB210 as UE
- 1xB210 as gNB

"""

tourInstructions = """

After all startup scripts have finished, and experiment is ready to start:

## Core Network ##

Start the 5G core network services. It will take several seconds for the services to start up. Make sure the script indicates that the services are healthy before moving on.

```
cd /var/tmp/oai-cn5g-fed/docker-compose

sudo python3 ./core-network.py --type start-mini --scenario 1
```

In another session, start following the logs for the AMF. This way you can see when the UE syncs with the network.

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

**After the UE associates (check from AMF logs in CN), open another session check the UE IP address.**

Check UE IP address
```
ifconfig oaitun_ue1
```
Add a route toward the CN for traffic gen node
```
sudo ip route add 192.168.70.0/24 dev oaitun_ue1
```
Check UE-CN reachability

# From UE to CN (in session on UE node)
```
ping 192.168.70.135
```

# From CN to UE (in session on cn node)
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
"""

BIN_PATH = "/local/repository/bin"
ETC_PATH = "/local/repository/etc"
LOWLAT_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:U18LL-SRSLTE"
UBUNTU_IMG = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD"
COTS_UE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:cots-jammy-image"
COMP_MANAGER_ID = "urn:publicid:IDN+emulab.net+authority+cm"

# old hash from branch bandwidth-testing-abs-sr-bsr-multiple_ue
#TODO: check if merged to develop or develop now supports multiple UEs
DEFAULT_NR_RAN_HASH = "1268b27c91be3a568dd352f2e9a21b3963c97432" # 2023.wk19
DEFAULT_NR_CN_HASH = "v1.5.0"

# DEFAULT_NR_RAN_HASH = "v2.0.0" 
# DEFAULT_NR_CN_HASH = "v2.0.0"

OAI_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-oai.sh")
WIFI_AP_NODE_ID="ayaz-ap"
WIFI_CLIENT_NODE_ID="ayaz-laptop"

def x310_node_pair(idx, x310_radio):
    role = "nodeb"
    node = request.RawPC("{}-gnb-comp".format(x310_radio))
    node.component_manager_id = COMP_MANAGER_ID
    node.hardware_type = params.sdr_nodetype

    if params.sdr_compute_image:
        node.disk_image = params.sdr_compute_image
    else:
        node.disk_image = UBUNTU_IMG

    node_radio_if = node.addInterface("usrp_if")
    node_radio_if.addAddress(rspec.IPv4Address("192.168.40.1", "255.255.255.0"))

    radio_link = request.Link("radio-link-{}".format(idx))
    radio_link.bandwidth = 10*1000*1000
    radio_link.addInterface(node_radio_if)

    radio = request.RawPC("{}-gnb-sdr".format(x310_radio))
    radio.component_id = x310_radio
    radio.component_manager_id = COMP_MANAGER_ID
    radio_link.addNode(radio)

    nodeb_cn_if = node.addInterface("nodeb-cn-if")
    nodeb_cn_if.addAddress(rspec.IPv4Address("192.168.1.{}".format(idx + 2), "255.255.255.0"))
    cn_link.addInterface(nodeb_cn_if)

    if params.oai_ran_commit_hash:
        oai_ran_hash = params.oai_ran_commit_hash
    else:
        oai_ran_hash = DEFAULT_NR_RAN_HASH

    cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
    node.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/common.sh"
    node.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/tune-cpu.sh"
    node.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/tune-sdr-iface.sh"
    node.addService(rspec.Execute(shell="bash", command=cmd))

    cmd = "{} '{}' {}".format(OAI_DEPLOY_SCRIPT, oai_ran_hash, role)
    node.addService(rspec.Execute(shell="bash", command=cmd))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))


def b210_nuc_pair_gnb(idx, b210_radio_gnb):
    role = "nodeb"
    gnb = request.RawPC("{}-gnb-comp".format(b210_radio_gnb))
    gnb.component_manager_id = COMP_MANAGER_ID
    gnb.component_id = b210_radio_gnb
    gnb.hardware_type = params.sdr_nodetype # d430

    nodeb_cn_if = gnb.addInterface("nodeb-cn-if")
    nodeb_cn_if.addAddress(rspec.IPv4Address("192.168.1.{}".format(idx + 2), "255.255.255.0"))
    cn_link.addInterface(nodeb_cn_if)

    if params.sdr_compute_image:
        gnb.disk_image = params.sdr_compute_image
    else:
        gnb.disk_image = UBUNTU_IMG

    if params.oai_ran_commit_hash:
        oai_ran_hash = params.oai_ran_commit_hash
    else:
        oai_ran_hash = DEFAULT_NR_RAN_HASH

    cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
    gnb.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/common.sh"
    gnb.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/tune-cpu.sh"
    gnb.addService(rspec.Execute(shell="bash", command=cmd))

    cmd = '{} "{}" {}'.format(OAI_DEPLOY_SCRIPT, oai_ran_hash, role)
    gnb.addService(rspec.Execute(shell="bash", command=cmd))
    # ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
    # ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))


# def b210_nuc_pair_ue(idx, b210_radio):
def b210_nuc_pair_ue(b210_radio):
    role = "ue"
    ue = request.RawPC("{}-ue-comp-".format(b210_radio))
    ue.component_manager_id = COMP_MANAGER_ID
    ue.component_id = b210_radio
    ue.hardware_type = params.sdr_nodetype # d430

    if params.sdr_compute_image:
        ue.disk_image = params.sdr_compute_image
    else:
        ue.disk_image = UBUNTU_IMG

    if params.oai_ran_commit_hash:
        oai_ran_hash = params.oai_ran_commit_hash
    else:
        oai_ran_hash = DEFAULT_NR_RAN_HASH

    cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
    ue.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/common.sh"
    ue.addService(rspec.Execute(shell="bash", command=cmd))

    cmd ="chmod +x /local/repository/bin/tune-cpu.sh"
    ue.addService(rspec.Execute(shell="bash", command=cmd))

    cmd = '{} "{}" {}'.format(OAI_DEPLOY_SCRIPT, oai_ran_hash, role)
    ue.addService(rspec.Execute(shell="bash", command=cmd))
    # ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
    # ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))




####
def UE_node_x310(idx, x310_radio):
	role = "ue"
	ue = request.RawPC("{}-ue-comp".format(x310_radio))
	ue.component_manager_id = COMP_MANAGER_ID
	ue.hardware_type = params.sdr_nodetype

	if params.sdr_compute_image:
		ue.disk_image = params.sdr_compute_image
	else:
		ue.disk_image = UBUNTU_IMG

	ue_radio_if = ue.addInterface("ue-usrp-if")
	# ue_radio_if.addAddress(rspec.IPv4Address("192.168.40.1", "255.255.255.0"))
	ue_radio_if.addAddress(rspec.IPv4Address("192.168.40.{}".format(idx + 2), "255.255.255.0"))

	radio_link = request.Link("radio-link-{}".format(idx))
	radio_link.bandwidth = 10*1000*1000
	radio_link.addInterface(ue_radio_if)

	radio = request.RawPC("{}-ue-sdr".format(x310_radio))
	radio.component_id = x310_radio
	radio.component_manager_id = COMP_MANAGER_ID
	radio_link.addNode(radio)

	if params.oai_ran_commit_hash:
		oai_ran_hash = params.oai_ran_commit_hash
	else:
		oai_ran_hash = DEFAULT_NR_RAN_HASH

	cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/common.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/tune-cpu.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/tune-sdr-iface.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd = '{} "{}" {}'.format(OAI_DEPLOY_SCRIPT, oai_ran_hash, role)
	ue.addService(rspec.Execute(shell="bash", command=cmd))
	ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
	ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))

####


def alloc_wifi_resources():
    # Allocate WiFi utility node
    util = request.RawPC("wifi-util")
    util.component_manager_id = COMP_MANAGER_ID
    util.hardware_type = params.util_nodetype
    if params.util_image:
        util.disk_image = params.util_image
    else:
        util.disk_image = UBUNTU_IMG
    util_if = util.addInterface("util-if")
    util_if.addAddress(rspec.IPv4Address("192.168.1.10", "255.255.255.0"))

    # Allocate WiFi access point
    wifiap = request.RawPC("wifi-ap")
    wifiap.component_manager_id = COMP_MANAGER_ID
    wifiap.component_id = WIFI_AP_NODE_ID

    # Allocate WiFi client laptop
    wificl = request.RawPC("wifi-client")
    wificl.component_manager_id = COMP_MANAGER_ID
    wificl.component_id = WIFI_CLIENT_NODE_ID

    # Connect WiFi utility node, ap, and client to a LAN
    wifi_lan = request.LAN("wifi-util-lan")
    wifi_lan.bandwidth = 1*1000*1000 # 1 Gbps
    wifi_lan.addInterface(util_if)
    wifi_lan.addNode(wifiap)
    wifi_lan.addNode(wificl)


pc = portal.Context()

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
]

pc.defineParameter(
    name="alloc_wifi",
    description="Allocate WiFi resources (access point and utilty server)?",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True
)

pc.defineParameter(
    name="sdr_nodetype",
    description="Type of compute node paired with the SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[1],
    legalValues=node_types
)

pc.defineParameter(
    name="cn_nodetype",
    description="Type of compute node to use for CN node (if included)",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[1],
    legalValues=node_types
)

pc.defineParameter(
    name="util_nodetype",
    description="Type of compute node to use for the WiFi utility server",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
    legalValues=node_types
)

pc.defineParameter(
    name="oai_ran_commit_hash",
    description="Commit hash for OAI RAN",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="oai_cn_commit_hash",
    description="Commit hash for OAI (5G)CN",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="sdr_compute_image",
    description="Image to use for compute connected to SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="util_image",
    description="Image to use for WiFi utility server",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

indoor_ota_x310s = [
    ("ota-x310-1", "gNB"),
    ("ota-x310-2", "UE X310 #2"),
    ("ota-x310-3", "UE X310 #3"),
    ("ota-x310-4", "UE X310 #4"),
]

indoor_ota_b210s = [
    ("ota-nuc1", "gNB"),
    ("ota-nuc2", "UE # 1"),
    ("ota-nuc3", "UE # 3"),
    ("ota-nuc4", "UE # 4"),
]


pc.defineParameter(
    name="b210_radio_gnb",
    description="B210 Radio (for OAI gNodeB)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_b210s[0],
    legalValues=indoor_ota_b210s
)

pc.defineParameter(
    name="b210_radio",
    description="b210 Radio (for OAI UE 1)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_b210s[1],
    legalValues=indoor_ota_b210s
)

pc.defineParameter(
    name="b210_radio",
    description="b210 Radio (for OAI UE 2)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_b210s[2],
    legalValues=indoor_ota_b210s
)

pc.defineParameter(
    name="b210_radio",
    description="b210 Radio (for OAI UE 3)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_b210s[3],
    legalValues=indoor_ota_b210s
)


pc.defineParameter(
    name="x310_radio",
    description="X310 Radio (for OAI gNodeB)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[0],
    legalValues=indoor_ota_x310s
)

pc.defineParameter(
    name="x310_radio_UE",
    description="x310 Radio (for OAI UE 1)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[1],
    legalValues=indoor_ota_x310s
)


pc.defineParameter(
    name="x310_radio_UE",
    description="x310 Radio (for OAI UE 2)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[2],
    legalValues=indoor_ota_x310s
)

pc.defineParameter(
    name="x310_radio_UE",
    description="x310 Radio (for OAI UE 3)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[3],
    legalValues=indoor_ota_x310s
)


portal.context.defineStructParameter(
    "freq_ranges", "Frequency Ranges To Transmit In",
    defaultValue=[{"freq_min": 5730.0, "freq_max": 5770.0}],
    multiValue=True,
    min=0,
    multiValueTitle="Frequency ranges to be used for transmission.",
    members=[
        portal.Parameter(
            "freq_min",
            "Frequency Range Min",
            portal.ParameterType.BANDWIDTH,
            3550.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
        portal.Parameter(
            "freq_max",
            "Frequency Range Max",
            portal.ParameterType.BANDWIDTH,
            3600.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
    ]
)

params = pc.bindParameters()
pc.verifyParameters()
request = pc.makeRequestRSpec()

role = "cn"
cn_node = request.RawPC("cn5g-docker-host")
cn_node.component_manager_id = COMP_MANAGER_ID
cn_node.hardware_type = params.cn_nodetype
cn_node.disk_image = UBUNTU_IMG
cn_if = cn_node.addInterface("cn-if")
cn_if.addAddress(rspec.IPv4Address("192.168.1.1", "255.255.255.0"))
cn_link = request.Link("cn-link")
# cn_link.bandwidth = 10*1000*1000
cn_link.addInterface(cn_if)

if params.oai_cn_commit_hash:
    oai_cn_hash = params.oai_cn_commit_hash
else:
    oai_cn_hash = DEFAULT_NR_CN_HASH

cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

cmd ="chmod +x /local/repository/bin/common.sh"
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

cmd = "{} '{}' {}".format(OAI_DEPLOY_SCRIPT, oai_cn_hash, role)
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

# Allocate wifi resources?
if params.alloc_wifi:
    alloc_wifi_resources()

# single x310 for gNB and UE for now
x310_node_pair(0, params.x310_radio)
UE_node_x310(1, params.x310_radio_UE)
#UE_node_x310(2, params.x310_radio_UE)


# single b210 for gNB
b210_nuc_pair_gnb(0, params.b210_radio_gnb)

# Single b210 for UE
# b210_nuc_pair_ue(1, params.b210_radio)
# b210_nuc_pair_ue(2, params.b210_radio)

# require all indoor OTA nucs for now
for b210_node in ["ota-nuc2", "ota-nuc3", "ota-nuc4"]:
    b210_nuc_pair_ue(b210_node)
	
for frange in params.freq_ranges:
    request.requestSpectrum(frange.freq_min, frange.freq_max, 0)

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.MARKDOWN, tourInstructions)
request.addTour(tour)

pc.printRequestRSpec(request)

