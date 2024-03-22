#!/usr/bin/env python

import os

import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.igext as IG
import geni.rspec.emulab.pnext as PN
import geni.rspec.emulab.spectrum as spectrum


tourDescription = """
### OAI 5G using the POWDER Indoor OTA Lab

This profile instantiates an experiment for testing OAI 5G with SDR-UEs in
standalone mode (SA) using resources in the POWDER indoor over-the-air (OTA) lab.
The indoor OTA lab includes:

- 1x NI X310 SDRs, each with a UBX-160 daughter card occupying channel 0. The
  TX/RX and RX2 ports on this channel are connected to broadband antennas. The
  SDRs are connected via fiber to near-edge compute resources.
- 1x NI B210 SDR for nrUE with a compute node

You can find a diagram of the lab layout here: [OTA Lab
Diagram](https://gitlab.flux.utah.edu/powderrenewpublic/powder-deployment/-/raw/master/diagrams/ota-lab.png)

The following will be deployed:

- 2 x d430 compute node to host the core network and UE
- 1 x d740 compute node for the gNodeB
- One of the four indoor OTA X310s for gNB
- One of the four indoor OTA x310s for UE

"""

tourInstructions = """

Startup scripts will still be running when your experiment becomes ready.
Watch the "Startup" column on the "List View" tab for your experiment and wait
until all of the compute nodes show "Finished" before proceeding.

After all startup scripts have finished...

On `cn`, start the 5G core network services. It will take several
seconds for the services to start up. Make sure the script indicates that the
services are healthy before moving on.

```
cd /var/tmp/oai-cn5g-fed/docker-compose
sudo python3 ./core-network.py --type start-mini --scenario 1
```

In another session, start following the logs for the AMF. This way you can
see when the UE syncs with the network.

```
sudo docker logs -f oai-amf
```

On `gNB` if using `band 78` with `PRB 106` :

```
sudo numactl --membind=0 --cpubind=0 \
  /var/tmp/oairan/cmake_targets/ran_build/build/nr-softmodem -E \
  -O /var/tmp/etc/oai/gnb.sa.band78.fr1.106PRB.usrpx310.conf --sa \
  --MACRLCs.[0].dl_max_mcs 28 --tune-offset 23040000
```
If using `band 46` with PRB `51`
```
sudo numactl --membind=0 --cpubind=0 \
  /var/tmp/oairan/cmake_targets/ran_build/build/nr-softmodem -E \
  -O /var/tmp/etc/oai/gnb.sa.band46.fr1.51PRB.usrpx310.conf --sa \
  --MACRLCs.[0].dl_max_mcs 28 --tune-offset 23040000
```

On `ue`:

After you've started the gNodeB, start the UE (include -E for some other bands):

```
sudo numactl --membind=0 --cpubind=0 \
  /var/tmp/oairan/cmake_targets/ran_build/build/nr-uesoftmodem\
  -O /var/tmp/etc/oai/ue.conf \
  -r 51 \
  -C 5754720000 \
  --ssb 186
  --usrp-args "clock_source=external,type=x300" \
  --band 46 \
  --numerology 1 \
  --ue-txgain 0 \
  --ue-rxgain 114 \
  --nokrnmod \
  --dlsch-parallel 4 \
  --sa
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
OAI_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-oai.sh")


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

def b210_nuc_pair(idx, b210_radio):
    role = "ue"
    ue = request.RawPC("{}-ue-comp".format(b210_radio))
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

pc = portal.Context()

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
]

pc.defineParameter(
    name="sdr_nodetype",
    description="Type of compute node paired with the SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
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

indoor_ota_x310s = [
    ("ota-x310-1",
     "USRP X310 #1"),
    ("ota-x310-2",
     "USRP X310 #2"),
]

indoor_ota_b210s = [
    ("ota-nuc1", "UE # 1"),
    ("ota-nuc4", "UE # 2"),
]


pc.defineParameter(
    name="x310_radio",
    description="X310 Radio (for OAI gNodeB)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[0],
    legalValues=indoor_ota_x310s
)

pc.defineParameter(
    name="b210_radio",
    description="b210 Radio (for OAI UE)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_b210s[0],
    legalValues=indoor_ota_b210s
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
cn_link.bandwidth = 10*1000*1000
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


# single x310 for gNB and UE for now
x310_node_pair(0, params.x310_radio)
# UE_node_x310(1, params.x310_radio_UE) #### This is for x310 UE

# Single b210 for UE
b210_nuc_pair(0, params.b210_radio)


for frange in params.freq_ranges:
    request.requestSpectrum(frange.freq_min, frange.freq_max, 0)

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.MARKDOWN, tourInstructions)
request.addTour(tour)

pc.printRequestRSpec(request)

