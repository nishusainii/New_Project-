# topics_data.py - Complete 72-Topic Curriculum Data Store for Palo Alto PAN-OS

def get_all_72_topics():
    topics = []

    # MODULE 1
    m1 = "Module 1: Initial Setup, Management Plane & Security Zone Architecture"
    topics.append({
        'module': m1, 'num': 1, 'title': 'Initial Configuration: Basics via GUI & CLI',
        'meaning': 'Establishing the out-of-band management IP, netmask, default gateway, DNS resolvers, and device hostname. This binds the dedicated MGT interface on the control plane, separating firewall management traffic from data plane user flows.',
        'example': 'Staging a fresh PA-VM in a lab environment with IP 172.17.0.50/16, gateway 172.17.0.1, primary DNS 8.8.8.8, secondary DNS 8.8.4.4, and hostname PA-VM-LAB.',
        'cli': """admin@PA-VM> configure
admin@PA-VM# set deviceconfig system type static
admin@PA-VM# set deviceconfig system ip-address 172.17.0.50 netmask 255.255.0.0 default-gateway 172.17.0.1
admin@PA-VM# set deviceconfig system dns-setting servers primary 8.8.8.8 secondary 8.8.4.4
admin@PA-VM# set deviceconfig system hostname PA-VM-LAB
admin@PA-VM# commit""",
        'gui': "1. Connect browser to <b>https://172.17.0.50</b> and log in.<br/>2. Navigate to: <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b>.<br/>3. Click <b>Gear (⚙️)</b> on <i>Management Interface Settings</i> &rarr; Type: <code>Static</code>, IP: <code>172.17.0.50</code>, Netmask: <code>255.255.0.0</code>, Gateway: <code>172.17.0.1</code> &rarr; Click <b>OK</b>.<br/>4. Click <b>Gear (⚙️)</b> on <i>General Settings</i> &rarr; Hostname: <code>PA-VM-LAB</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m1, 'num': 2, 'title': 'Initial Configuration: Security Zone Implementation',
        'meaning': 'Palo Alto firewalls enforce a Zero-Trust architecture where all interfaces must belong to a Security Zone. Traffic between different zones is blocked by default until an explicit Security Policy rule allows it; traffic within the same zone is allowed by default.',
        'example': 'Creating four network zones: INSIDE (Trust LAN), DMZ1 (Web Servers), OUTSIDE (Untrust WAN), and DMZ2 (Database Servers), binding them to physical ports ethernet1/1 through ethernet1/4.',
        'cli': """admin@PA-VM# set zone INSIDE network layer3 ethernet1/1
admin@PA-VM# set zone DMZ1 network layer3 ethernet1/2
admin@PA-VM# set zone OUTSIDE network layer3 ethernet1/3
admin@PA-VM# set zone DMZ2 network layer3 ethernet1/4
admin@PA-VM# commit
admin@PA-VM> show zone""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Zones</b> &rarr; Click <b>Add</b>.<br/>2. Name: <code>INSIDE</code> &rarr; Type: <code>Layer3</code> &rarr; Under <i>Interfaces</i>, click <b>Add</b> &rarr; Select <code>ethernet1/1</code> &rarr; Click <b>OK</b>.<br/>3. Repeat for <code>DMZ1</code> (ethernet1/2), <code>OUTSIDE</code> (ethernet1/3), and <code>DMZ2</code> (ethernet1/4) &rarr; Click <b>Commit</b>."
    })

    # MODULE 2
    m2 = "Module 2: IPv4 Static Routing, Default Gateway & Path Monitoring"
    topics.append({
        'module': m2, 'num': 3, 'title': 'Interface Configuration: IPv4 Static Routing GUI/CLI',
        'meaning': 'Manually programming destination network prefixes into the Virtual Router table pointing to a specific next-hop IP address or outgoing interface. Static routes have an administrative distance (metric) of 10 by default.',
        'example': 'Directing corporate user traffic destined for branch server pool 10.20.0.0/16 to the DMZ1 router next-hop 192.168.2.1 via interface ethernet1/2.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route Route-DMZ1-Pool destination 10.20.0.0/16 interface ethernet1/2 nexthop ip-address 192.168.2.1 metric 10
admin@PA-VM# commit
admin@PA-VM> show routing route virtual-router default""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <b>default</b>.<br/>2. Select <b>Static Routes</b> &rarr; <b>IPv4</b> &rarr; Click <b>Add</b>.<br/>3. Name: <code>Route-DMZ1-Pool</code> &rarr; Destination: <code>10.20.0.0/16</code> &rarr; Interface: <code>ethernet1/2</code> &rarr; Next Hop: <code>IP Address</code> &rarr; Value: <code>192.168.2.1</code> &rarr; Metric: <code>10</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m2, 'num': 4, 'title': 'Interface Configuration: IPv4 Default Routing GUI/CLI',
        'meaning': 'The gateway of last resort (quad-zero 0.0.0.0/0). Any packet whose destination IP does not match any specific route in the routing table is forwarded out this default path to the upstream ISP router.',
        'example': 'Routing all unmapped public Internet traffic out interface ethernet1/3 to the primary ISP border gateway at 192.168.3.1.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route Default-Route destination 0.0.0.0/0 interface ethernet1/3 nexthop ip-address 192.168.3.1 metric 10
admin@PA-VM# commit
admin@PA-VM> show routing fib virtual-router default""",
        'gui': "1. In <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>Static Routes</b> &rarr; <b>IPv4</b>.<br/>2. Click <b>Add</b> &rarr; Name: <code>Default-Route</code> &rarr; Destination: <code>0.0.0.0/0</code> &rarr; Interface: <code>ethernet1/3</code> &rarr; Next Hop IP: <code>192.168.3.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m2, 'num': 5, 'title': 'Interface Configuration: IPv4 Path Monitoring GUI/CLI',
        'meaning': 'Attaching continuous ICMP keepalive health probes to a static route. If the monitored upstream target stops responding, PAN-OS invalidates the static route and pulls it from the active Forwarding Information Base (FIB), enabling automated dual-ISP failover.',
        'example': 'Probing upstream DNS 8.8.8.8 sourced from ethernet1/3 (192.168.3.2) every 3 seconds. If 5 consecutive pings fail, withdraw the primary ISP default route so backup ISP route (metric 20) takes over.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route ISP1-Default destination 0.0.0.0/0 interface ethernet1/3 nexthop ip-address 192.168.3.1 metric 10 path-monitor monitor-destinations Mon-DNS enable yes source 192.168.3.2 destination 8.8.8.8 interval 3 count 5
admin@PA-VM# set network virtual-router default routing-table ip static-route ISP1-Default path-monitor enable yes failure-condition any
admin@PA-VM# commit
admin@PA-VM> show routing path-monitor""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>Static Routes</b> &rarr; Edit <code>ISP1-Default</code>.<br/>2. Select <b>Path Monitor</b> tab &rarr; Check <b>Enable</b> &rarr; Condition: <code>Any</code>.<br/>3. Click <b>Add</b> &rarr; Name: <code>Mon-DNS</code> &rarr; Dest: <code>8.8.8.8</code>, Source: <code>192.168.3.2</code>, Interval: <code>3</code>, Count: <code>5</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    # MODULE 3
    m3 = "Module 3: Advanced Routing — IPv4 RIP (Routing Information Protocol)"
    topics.append({
        'module': m3, 'num': 6, 'title': 'Advance-Routing: IPv4 RIP GUI/CLI',
        'meaning': 'Enabling the distance-vector Routing Information Protocol (RIPv2) on the virtual router. RIP uses hop count as its metric (maximum 15 hops; 16 represents infinity/unreachable).',
        'example': 'Activating RIP routing engine on virtual router default to interoperate with legacy edge switches.',
        'cli': """admin@PA-VM# set network virtual-router default rip enable yes
admin@PA-VM# commit""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <b>default</b>.<br/>2. Select the <b>RIP</b> tab &rarr; Check the <b>Enable</b> box &rarr; Click <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 7, 'title': 'Advance-Routing: IPv4 RIP Lab-Basic',
        'meaning': 'Configuring RIP Interface Groups to determine which firewall interfaces broadcast and listen for RIPv2 multicast updates on 224.0.0.9 (UDP port 520).',
        'example': 'Binding interface ethernet1/1 (peer to Router-1) and ethernet1/2 (peer to Router-2) to RIP-Group1 in normal mode.',
        'cli': """admin@PA-VM# set network virtual-router default rip interface-groups RIP-Group1 interface ethernet1/1 mode normal
admin@PA-VM# set network virtual-router default rip interface-groups RIP-Group1 interface ethernet1/2 mode normal
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>RIP</b> &rarr; <b>Interface Groups</b>.<br/>2. Click <b>Add</b> &rarr; Name: <code>RIP-Group1</code> &rarr; Under <i>Interfaces</i>, add <code>ethernet1/1</code> and <code>ethernet1/2</code> (Mode: <code>normal</code>) &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 8, 'title': 'Advance-Routing: IPv4 RIP Lab-Routing Table Verification',
        'meaning': 'Auditing the Routing Information Base (RIB) to verify which dynamic prefixes have been learned from adjacent RIP routers, along with their hop counts and next-hop IPs.',
        'example': 'Confirming that remote branch subnet 10.10.1.0/24 is learned via RIP from neighbor 192.168.1.1 with a hop count of 2.',
        'cli': """admin@PA-VM> show routing protocol rip route
admin@PA-VM> show routing route protocol rip virtual-router default""",
        'gui': "1. Go to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <b>More Runtime Stats</b> on <code>default</code>.<br/>2. Select <b>Routing Table</b> tab &rarr; Filter flag <b>R</b> (RIP) to observe prefix, next-hop, and metric."
    })

    topics.append({
        'module': m3, 'num': 9, 'title': 'Advance-Routing: IPv4 RIP Lab-Peer Table Verification',
        'meaning': 'Validating active RIP neighbors, verifying peer reachability, last update received timestamp, and detecting silent or timed-out routers.',
        'example': 'Checking neighbor table to verify peer 192.168.1.1 has communicated within the last 30 seconds.',
        'cli': """admin@PA-VM> show routing protocol rip peer
admin@PA-VM> show routing protocol rip interface""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; Select <b>RIP</b> tab.<br/>2. Click <b>Peers</b> to inspect neighbor IP, status, and last update received timestamp."
    })

    topics.append({
        'module': m3, 'num': 10, 'title': 'Advance-Routing: IPv4 RIP Lab-Redistribution',
        'meaning': 'Injecting non-RIP routes (such as directly connected LAN subnets or static routes) into RIP update advertisements so neighboring routers discover them.',
        'example': 'Redistributing local connected subnets into RIP with metric 2 so Router-1 and Router-2 learn firewall local LAN networks.',
        'cli': """admin@PA-VM# set network virtual-router default rip-redist-rules Redist-Connected enable yes metric 2 route-table unicast filter match-route-type connect
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>RIP</b> &rarr; <b>Redistribution Rules</b>.<br/>2. Click <b>Add</b> &rarr; Name: <code>Redist-Connected</code> &rarr; Metric: <code>2</code> &rarr; Filter: Check <b>connect</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 11, 'title': 'Advance-Routing: IPv4 RIP Lab-Timer Modification',
        'meaning': 'Tuning RIP update (default 30s), route timeout (default 180s), and garbage collection (default 120s) timers. Modifying these timers accelerates network convergence after link failures.',
        'example': 'Adjusting RIP update timer to 15s, timeout to 90s, and garbage collection to 60s for 2x faster failover in a high-speed LAN.',
        'cli': """admin@PA-VM# set network virtual-router default rip timers update 15 timeout 90 garbage-collection 60
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>RIP</b> &rarr; <b>Timers</b>.<br/>2. Set Update: <code>15</code>, Timeout: <code>90</code>, Garbage Collection: <code>60</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 12, 'title': 'Advance-Routing: IPv4 RIP Lab-Advertise Default-Route',
        'meaning': 'Instructing the firewall to generate and advertise a default route (0.0.0.0/0) in its RIP updates, pointing downstream routers toward the firewall for all external traffic.',
        'example': 'Advertising default route with metric 1 to all RIP peers so branch routers send all Internet-bound packets to the firewall.',
        'cli': """admin@PA-VM# set network virtual-router default rip default-route-advertise enable yes metric 1
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>RIP</b>.<br/>2. Under <i>Default Route</i> &rarr; Check <b>Advertise</b> &rarr; Metric: <code>1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 13, 'title': 'Advance-Routing: IPv4 RIP Lab-Authentication',
        'meaning': 'Securing RIPv2 packet updates with MD5 cryptographic authentication to prevent unauthorized routers from spoofing routing updates or poisoning the routing table.',
        'example': 'Configuring MD5 authentication with Key ID 1 and shared key SecretKey123 on interface group RIP-Group1.',
        'cli': """admin@PA-VM# set network virtual-router default rip interface-groups RIP-Group1 authentication md5 key-id 1 key SecretKey123
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>RIP</b> &rarr; Click <code>RIP-Group1</code>.<br/>2. Authentication: Select <code>MD5</code> &rarr; Key ID: <code>1</code> &rarr; Key: <code>SecretKey123</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m3, 'num': 14, 'title': 'Advance-Routing: IPv4 RIP Troubleshoot',
        'meaning': 'Diagnosing RIP protocol issues, including count-to-infinity routing loops, split-horizon hold-downs, authentication mismatches, and firewall security policy drops on UDP 520.',
        'example': 'Enabling routing engine debug tracing and tailing routed.log to detect rejected unauthenticated packets from neighbor 192.168.1.1.',
        'cli': """admin@PA-VM> show routing protocol rip status
admin@PA-VM> debug routing pfe rip all on
admin@PA-VM> tail follow yes mp-log routed.log""",
        'gui': "1. Go to: <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>System</b> &rarr; Filter: <code>(subtype eq routing) and (description contains 'rip')</code>.<br/>2. Inspect authentication mismatches, metric 16 unreachable errors, and packet drop events."
    })

    # MODULE 4
    m4 = "Module 4: Enterprise IPv4 OSPF (Open Shortest Path First) Architecture"
    topics.append({
        'module': m4, 'num': 15, 'title': 'Advance-Routing: IPv4 OSPF GUI/CLI',
        'meaning': 'Enabling the link-state OSPFv2 protocol engine on the virtual router and assigning a unique 32-bit dotted-decimal Router-ID to identify the firewall within the autonomous system.',
        'example': 'Enabling OSPF on virtual router default with Router-ID 1.1.1.1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf enable yes router-id 1.1.1.1
admin@PA-VM# commit""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <b>default</b> &rarr; <b>OSPF</b> tab.<br/>2. Check <b>Enable</b> &rarr; Router ID: <code>1.1.1.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 16, 'title': 'Advance-Routing: IPv4 OSPF Lab-Basic and Multi-Area',
        'meaning': 'Configuring a hierarchical multi-area OSPF design. Area 0 (Backbone) connects to core distribution switches, while non-backbone areas isolate flooding domains and reduce SPF recalculation overhead.',
        'example': 'Binding ethernet1/1 to backbone Area 0.0.0.0 and ethernet1/2 to branch Area 0.0.0.1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.0 type normal interface ethernet1/1 enable yes
admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.1 type normal interface ethernet1/2 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; <b>Areas</b>.<br/>2. Add Area <code>0.0.0.0</code> (Type: <code>normal</code>, Interface: <code>ethernet1/1</code>).<br/>3. Add Area <code>0.0.0.1</code> (Type: <code>normal</code>, Interface: <code>ethernet1/2</code>) &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 17, 'title': 'Advance-Routing: IPv4 OSPF Lab-Neighbor Table Verification',
        'meaning': 'Auditing OSPF neighbor adjacency states. On broadcast multi-access links, neighbors must transition through Down, Init, 2-Way, ExStart, Exchange, Loading, to Full (DR, BDR, or DROther).',
        'example': 'Verifying neighbor 192.168.1.1 on ethernet1/1 is in Full state as Designated Router (DR).',
        'cli': """admin@PA-VM> show routing protocol ospf neighbor
admin@PA-VM> show routing protocol ospf neighbor detail""",
        'gui': "1. Go to: <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>OSPF</b> &rarr; <b>Neighbors</b>.<br/>2. Confirm neighbor status shows <b>Full</b> with DR/BDR role clearly indicated."
    })

    topics.append({
        'module': m4, 'num': 18, 'title': 'Advance-Routing: IPv4 OSPF Lab-Database Table Verification',
        'meaning': 'Auditing the Link-State Database (LSDB). All routers in an area must have an identical LSDB containing Router LSAs (Type 1), Network LSAs (Type 2), Summary LSAs (Type 3), and External LSAs (Type 5).',
        'example': 'Inspecting the LSDB to ensure all router and network LSAs for Area 0 are synchronized with Router-1.',
        'cli': """admin@PA-VM> show routing protocol ospf dump
admin@PA-VM> show routing protocol ospf lsdb""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>OSPF</b> &rarr; <b>Link State Database</b>.<br/>2. Inspect LSA counts by type (Router, Network, Summary, AS-External)."
    })

    topics.append({
        'module': m4, 'num': 19, 'title': 'Advance-Routing: IPv4 OSPF Lab-Routing Table Verification',
        'meaning': 'Verifying OSPF routes installed into the firewall active routing table (FIB) after Dijkstra algorithm computation. Marked with flags: O (Intra-area), Oo (Inter-area), or O1/O2 (External).',
        'example': 'Confirming intra-area route 10.10.1.0/24 is installed with next-hop 192.168.1.1 and metric 11.',
        'cli': """admin@PA-VM> show routing protocol ospf route
admin@PA-VM> show routing route protocol ospf virtual-router default""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>Routing Table</b>.<br/>2. Filter by flags <b>O</b>, <b>Oo</b>, <b>O1</b>, <b>O2</b> to inspect installed prefixes and metrics."
    })

    topics.append({
        'module': m4, 'num': 20, 'title': 'Advance-Routing: IPv4 OSPF Lab-Virtual-Links',
        'meaning': 'Creating a logical link through a non-backbone transit area to reconnect a partitioned area back to Area 0. All OSPF non-backbone areas must connect directly to Area 0; virtual links solve non-contiguous topologies.',
        'example': 'Connecting isolated Area 2 through transit Area 1 to reach Area 0, targeting neighbor router ID 3.3.3.3.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.1 virtual-link VL-to-R3 enable yes neighbor-id 3.3.3.3 transit-area-id 0.0.0.1
admin@PA-VM# commit
admin@PA-VM> show routing protocol ospf virtual-link""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Click transit area <code>0.0.0.1</code>.<br/>2. Select <b>Virtual Link</b> tab &rarr; Add <code>VL-to-R3</code> &rarr; Neighbor: <code>3.3.3.3</code>, Transit: <code>0.0.0.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 21, 'title': 'Advance-Routing: IPv4 OSPF Lab-Hello Interval Modification',
        'meaning': 'Changing the frequency of OSPF Hello packets sent on an interface (default 10s on broadcast links). Both neighbor routers must have identical Hello intervals to form an adjacency.',
        'example': 'Lowering Hello interval on ethernet1/1 to 5s for rapid link-down detection in a datacenter.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 hello-interval 5
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Area <code>0.0.0.0</code> &rarr; Click <code>ethernet1/1</code>.<br/>2. Set <b>Hello Interval</b>: <code>5</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 22, 'title': 'Advance-Routing: IPv4 OSPF Lab-Dead Interval Modification',
        'meaning': 'The time a router waits without receiving a Hello packet before declaring the neighbor dead (default 40s, typically 4x Hello). Must match across peers.',
        'example': 'Setting Dead interval to 20s to match the 5s Hello interval on ethernet1/1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 dead-counts 20
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Area <code>0.0.0.0</code> &rarr; Click <code>ethernet1/1</code>.<br/>2. Set <b>Dead Interval</b>: <code>20</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 23, 'title': 'Advance-Routing: IPv4 OSPF Lab-Authentication',
        'meaning': 'Encrypting OSPF packet exchanges using MD5 message digests. Routers verify key-id and password hash on every packet, blocking rogue routers from forming adjacencies.',
        'example': 'Configuring MD5 authentication with Key ID 1 and password PaloAltoOspfPass1! on interface ethernet1/1 in Area 0.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 authentication md5 key-id 1 key PaloAltoOspfPass1!
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Area <code>0.0.0.0</code> &rarr; Click <code>ethernet1/1</code>.<br/>2. Authentication: <code>MD5</code> &rarr; Key ID: <code>1</code> &rarr; Key: <code>PaloAltoOspfPass1!</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 24, 'title': 'Advance-Routing: IPv4 OSPF Lab-Stub Area',
        'meaning': 'Configuring an area to block external Type 4 and Type 5 LSAs. The ABR automatically generates a default route (Type 3 summary) into the stub area, dramatically reducing routing table size.',
        'example': 'Configuring branch Area 0.0.0.2 as a Stub Area with default route metric 10 to protect memory on branch firewalls.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.2 type stub default-route metric 10
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; <b>Areas</b> &rarr; Add Area <code>0.0.0.2</code>.<br/>2. Type: <code>stub</code> &rarr; Default Route Metric: <code>10</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 25, 'title': 'Advance-Routing: IPv4 OSPF Lab-Totally Stub Area',
        'meaning': 'Extending Stub areas by blocking both External LSAs (Type 4/5) AND Inter-Area Summary LSAs (Type 3). The ABR injects only a single default route into the area.',
        'example': 'Disabling summary LSA acceptance on Stub Area 0.0.0.2 so branch routers have only intra-area routes plus a default route.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.2 type stub accepts-summary-lsa no
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Click Area <code>0.0.0.2</code>.<br/>2. Type: <code>stub</code> &rarr; Uncheck <b>Accept Summary LSA</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 26, 'title': 'Advance-Routing: IPv4 OSPF Lab-Totally NSSA Area',
        'meaning': 'Not-So-Stubby Area that blocks external Type 5 LSAs from the backbone but permits local route redistribution via Type 7 LSAs. Totally NSSA also suppresses Type 3 summary LSAs.',
        'example': 'Configuring Area 0.0.0.3 as Totally NSSA so a local router can redistribute RIP/BGP routes while keeping the area shielded from outside LSAs.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.3 type nssa accepts-summary-lsa no
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Add Area <code>0.0.0.3</code>.<br/>2. Type: <code>nssa</code> &rarr; Uncheck <b>Accept Summary LSA</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 27, 'title': 'Advance-Routing: IPv4 OSPF Lab-External Summarization',
        'meaning': 'Summarizing external routes redistributed into OSPF at the ASBR boundary. A single Type 5 summary LSA is flooded instead of dozens of granular external subnets.',
        'example': 'Summarizing redistributed internal server subnets under 10.0.0.0/8 so neighboring OSPF routers receive one aggregate route.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf asbr-summary 10.0.0.0/8 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; <b>ASBR Summary</b>.<br/>2. Click <b>Add</b> &rarr; Prefix: <code>10.0.0.0/8</code> &rarr; Check <b>Enable</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 28, 'title': 'Advance-Routing: IPv4 OSPF Lab-Inter-Area Summarization',
        'meaning': 'Summarizing multiple contiguous /24 prefixes within an area at the Area Border Router (ABR) boundary into a single Type 3 Summary LSA advertised into Area 0.',
        'example': 'Aggregating subnets 192.168.1.0/24 through 192.168.4.0/24 into 192.168.0.0/16 at the Area 1 border.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf area 0.0.0.1 range 192.168.0.0/16 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; Click Area <code>0.0.0.1</code>.<br/>2. Select <b>Range</b> &rarr; Add Range: <code>192.168.0.0/16</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 29, 'title': 'Advance-Routing: IPv4 OSPF Lab-Default-Information-Originate',
        'meaning': 'Generating a Type 5 External default route (0.0.0.0/0) and advertising it across all OSPF areas so all internal routers use the firewall as their egress Internet gateway.',
        'example': 'Originating default route with metric 10 and metric type ext-2 into the OSPF domain.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf default-information-originate enable yes metric 10 metric-type ext-2
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPF</b> &rarr; <b>Export Rules</b>.<br/>2. Check <b>Default Information Originate</b> &rarr; Metric: <code>10</code>, Metric Type: <code>ext-2</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 30, 'title': 'Advance-Routing: IPv4 OSPF Lab-Redistribution',
        'meaning': 'Exporting Connected, Static, or BGP routes into the OSPF domain via redistribution profiles, converting foreign routes into OSPF Type 5 External LSAs.',
        'example': 'Redistributing all directly connected interfaces into OSPF with metric 20 and metric-type ext-2.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospf export-rules Redist-LAN enable yes metric 20 metric-type ext-2
admin@PA-VM# set network virtual-router default redist-profile Redist-Profile-1 filter match-route-type connect
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>Redistribution Profiles</b> &rarr; Add <code>Redist-Profile-1</code> (Filter: <code>connect</code>).<br/>2. Go to <b>OSPF</b> &rarr; <b>Export Rules</b> &rarr; Add rule referencing profile &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m4, 'num': 31, 'title': 'Advance-Routing: IPv4 OSPF Troubleshoot',
        'meaning': 'Diagnosing OSPF neighbor stalls: stuck in Init (one-way hello/security policy dropping multicast 224.0.0.5), stuck in 2-Way (DROther behavior), or stuck in ExStart/Exchange (MTU mismatch).',
        'example': 'Tailing routed.log to detect MTU mismatch where firewall MTU is 1500 and peer MTU is 9000, causing DBD exchange drops.',
        'cli': """admin@PA-VM> show routing protocol ospf status
admin@PA-VM> show routing protocol ospf interface
admin@PA-VM> debug routing pfe ospf all on
admin@PA-VM> tail follow yes mp-log routed.log""",
        'gui': "1. Go to: <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>System</b> &rarr; Filter: <code>(description contains 'ospf')</code>.<br/>2. Verify interface MTU matches neighbor; confirm security policy allows IP protocol 89."
    })

    # MODULE 5
    m5 = "Module 5: Enterprise IPv4 BGP (Border Gateway Protocol) Architecture"
    topics.append({
        'module': m5, 'num': 32, 'title': 'Advance-Routing: IPv4 BGP GUI/CLI',
        'meaning': 'Enabling the path-vector Border Gateway Protocol (BGPv4) daemon on the firewall virtual router, configuring the local Autonomous System Number (ASN), and establishing the Router-ID.',
        'example': 'Configuring local private AS 65001 with BGP Router-ID 1.1.1.1 on virtual router default.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp enable yes as 65001 router-id 1.1.1.1
admin@PA-VM# commit""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <b>default</b> &rarr; <b>BGP</b> tab.<br/>2. Check <b>Enable</b> &rarr; AS Number: <code>65001</code> &rarr; Router ID: <code>1.1.1.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 33, 'title': 'Advance-Routing: IPv4 BGP Lab-Basic',
        'meaning': 'Configuring a Peer Group and establishing an external BGP (eBGP) peering session over TCP port 179 to an upstream ISP router in a different autonomous system.',
        'example': 'Establishing eBGP session from local interface ethernet1/3 (192.168.3.2 in AS 65001) to ISP border router 192.168.3.1 in AS 65002.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-ISP type external
admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-ISP peer ISP-Router peer-as 65002 local-address ip 192.168.3.2/24 interface ethernet1/3 peer-address ip 192.168.3.1 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Peer Group</b> &rarr; Click <b>Add</b>.<br/>2. Name: <code>eBGP-ISP</code> &rarr; Type: <code>ebgp</code>.<br/>3. Peer: Add <code>ISP-Router</code> &rarr; Peer AS: <code>65002</code>, Peer IP: <code>192.168.3.1</code>, Interface: <code>ethernet1/3</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 34, 'title': 'Advance-Routing: IPv4 BGP Lab-Neighbor Table Verification',
        'meaning': 'Auditing the BGP neighbor state machine. Verifying that the TCP 179 session has progressed through Idle, Connect, Active, OpenSent, OpenConfirm to Established.',
        'example': 'Running show routing protocol bgp summary to confirm peer 192.168.3.1 is in Established state with active prefix exchange.',
        'cli': """admin@PA-VM> show routing protocol bgp peer
admin@PA-VM> show routing protocol bgp summary""",
        'gui': "1. Go to: <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>BGP</b> &rarr; <b>Peer</b>.<br/>2. Confirm Status = <b>Established</b>, Uptime is active, and prefixes are received."
    })

    topics.append({
        'module': m5, 'num': 35, 'title': 'Advance-Routing: IPv4 BGP Lab-BGP Table Verification',
        'meaning': 'Inspecting the BGP Link-State RIB table (Loc-RIB, Adj-RIB-In, Adj-RIB-Out). Auditing path attributes including AS-Path, Weight, Local Preference, Multi-Exit Discriminator (MED), and Next-Hop.',
        'example': 'Verifying route 10.30.1.0/24 in Loc-RIB with AS-Path 65002 and Local Preference 100.',
        'cli': """admin@PA-VM> show routing protocol bgp loc-rib
admin@PA-VM> show routing protocol bgp rib-out""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>BGP</b> &rarr; <b>Loc-RIB</b>.<br/>2. Inspect path attributes (AS-Path, Next Hop, Local Preference, MED) for all advertised and received routes."
    })

    topics.append({
        'module': m5, 'num': 36, 'title': 'Advance-Routing: IPv4 BGP Lab-Routing Table Verification',
        'meaning': 'Verifying that the best BGP routes selected by the BGP decision algorithm have been successfully committed to the active FIB with flag B (BGP Unicast).',
        'example': 'Confirming external prefix 10.30.1.0/24 is active in the routing table with next-hop 192.168.3.1 and flag A S / A B.',
        'cli': """admin@PA-VM> show routing route protocol bgp virtual-router default""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>Routing Table</b>.<br/>2. Filter by flag <b>B</b> to inspect all operational BGP forwarding entries."
    })

    topics.append({
        'module': m5, 'num': 37, 'title': 'Advance-Routing: IPv4 BGP Lab-Next-Hop-Self',
        'meaning': 'When an eBGP route is advertised to an internal iBGP peer, BGP preserves the original external next-hop IP by default. Next-Hop-Self forces the firewall to rewrite the next-hop IP to its own internal interface address so internal peers can resolve the route.',
        'example': 'Configuring Next-Hop-Self on peer Core-Switch so that all eBGP ISP routes have next-hop rewritten to the firewall internal IP 192.168.1.2.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group iBGP-Peers peer Core-Switch next-hop use-self
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Peer Group</b> &rarr; Select peer.<br/>2. In <i>Connection Options</i> &rarr; Next Hop: Select <b>Use Self</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 38, 'title': 'Advance-Routing: IPv4 BGP Lab-Route-Reflector-Client',
        'meaning': 'Internal BGP (iBGP) prohibits advertising routes learned from one iBGP peer to another iBGP peer (split-horizon). Route Reflectors bypass this rule, allowing routers to reflect iBGP routes without requiring a full mesh of peerings.',
        'example': 'Designating Core-Switch as a Route Reflector Client under cluster-id 1.1.1.1 on the firewall.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group iBGP-Peers peer Core-Switch ref-client client
admin@PA-VM# set network virtual-router default protocol bgp router-id 1.1.1.1 cluster-id 1.1.1.1
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select iBGP Peer.<br/>2. Set <b>Reflector Client</b>: <code>client</code> &rarr; Set Cluster ID: <code>1.1.1.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 39, 'title': 'Advance-Routing: IPv4 BGP Lab-Authentication',
        'meaning': 'Enforcing TCP MD5 cryptographic signatures (RFC 2385) on BGP TCP port 179 connections. Prevents TCP reset attacks and spoofed BGP route injections.',
        'example': 'Configuring MD5 password BGPSecretKey99! on the eBGP ISP peering.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-ISP peer ISP-Router authentication md5 key BGPSecretKey99!
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select Peer &rarr; <b>Authentication</b>.<br/>2. Check <b>Authentication</b> &rarr; Type: <code>MD5</code> &rarr; Key: <code>BGPSecretKey99!</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 40, 'title': 'Advance-Routing: IPv4 BGP Lab-Aggregation',
        'meaning': 'Generating a summarized CIDR supernet advertisement while suppressing granular internal subnets (summary-only). Conserves global BGP routing table memory.',
        'example': 'Aggregating subnets under 10.0.0.0/8 and advertising only the /8 supernet to the ISP while suppressing internal /24 subnets.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp aggregate 10.0.0.0/8 enable yes summary-only yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Aggregations</b>.<br/>2. Click <b>Add</b> &rarr; Prefix: <code>10.0.0.0/8</code> &rarr; Check <b>Enable</b> &rarr; Check <b>Summary Only</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 41, 'title': 'Advance-Routing: IPv4 BGP Lab-Redistribution',
        'meaning': 'Injecting connected, static, or OSPF routes into BGP advertisements sent to external autonomous systems via export rules and redistribution profiles.',
        'example': 'Exporting corporate public IP block 192.168.1.0/24 into BGP to announce it to the upstream ISP.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp export-rules Export-to-ISP enable yes match-address-prefix 192.168.1.0/24
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Export</b> tab.<br/>2. Click <b>Add</b> &rarr; Name: <code>Export-to-ISP</code> &rarr; Match Prefix: <code>192.168.1.0/24</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m5, 'num': 42, 'title': 'Advance-Routing: IPv4 BGP Troubleshoot',
        'meaning': 'Resolving BGP state machine failures. Diagnosing why a peer is stuck in Active state (TCP 179 dropped by firewall security policy, wrong peer IP, wrong local IP, or eBGP multihop TTL issue).',
        'example': 'Resetting a stuck BGP peering session and inspecting routed.log for AS-Path loop detection or TCP handshake resets.',
        'cli': """admin@PA-VM> show routing protocol bgp summary
admin@PA-VM> show routing protocol bgp peer detail
admin@PA-VM> test routing bgp peer-reset peer-group eBGP-ISP
admin@PA-VM> tail follow yes mp-log routed.log""",
        'gui': "1. Go to: <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>System</b> &rarr; Filter: <code>(description contains 'bgp')</code>.<br/>2. If peering is in 'Active' state, ensure Security Policy allows application 'bgp' (TCP 179) between the peering zones."
    })

    # MODULE 6
    m6 = "Module 6: Advanced IPv6 Routing, Default Gateways & Path Monitoring"
    topics.append({
        'module': m6, 'num': 43, 'title': 'Advance-Routing: IPv6 Static Routing GUI/CLI',
        'meaning': 'Configuring 128-bit IPv6 static route entries in the virtual router pointing to an IPv6 next-hop address or egress interface.',
        'example': 'Routing IPv6 enterprise subnet 2001:db8:2::/64 out ethernet1/2 to next-hop 2001:db8:2::1.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route-ipv6 Route-IPv6-DMZ1 destination 2001:db8:2::/64 interface ethernet1/2 nexthop ipv6-address 2001:db8:2::1 metric 10
admin@PA-VM# commit
admin@PA-VM> show routing route ipv6-only yes""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>Static Routes</b> &rarr; <b>IPv6</b>.<br/>2. Click <b>Add</b> &rarr; Dest: <code>2001:db8:2::/64</code>, Interface: <code>ethernet1/2</code>, Next Hop: <code>2001:db8:2::1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m6, 'num': 44, 'title': 'Advance-Routing: IPv6 Default Routing GUI/CLI',
        'meaning': 'Configuring the global IPv6 default route (::/0) forwarding all unmapped IPv6 internet traffic out the external WAN gateway.',
        'example': 'Forwarding all IPv6 traffic out ethernet1/3 to the ISP IPv6 gateway at 2001:db8:3::1.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route-ipv6 Default-IPv6 destination ::/0 interface ethernet1/3 nexthop ipv6-address 2001:db8:3::1 metric 10
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>Static Routes</b> &rarr; <b>IPv6</b>.<br/>2. Click <b>Add</b> &rarr; Dest: <code>::/0</code> &rarr; Interface: <code>ethernet1/3</code> &rarr; Next Hop: <code>2001:db8:3::1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m6, 'num': 45, 'title': 'Advance-Routing: IPv6 Path Monitoring GUI/CLI',
        'meaning': 'Attaching ICMPv6 ping health checks to an IPv6 static route. If the monitored IPv6 address stops responding, the route is pulled from the FIB to prevent blackholing IPv6 traffic.',
        'example': 'Monitoring Google Public IPv6 DNS 2001:4860:4860::8888 every 3s. If 5 pings fail, deactivate primary IPv6 default route.',
        'cli': """admin@PA-VM# set network virtual-router default routing-table ip static-route-ipv6 Default-IPv6 path-monitor enable yes failure-condition any monitor-destinations Mon-IPv6-DNS enable yes destination 2001:4860:4860::8888 interval 3 count 5
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>Static Routes</b> &rarr; <b>IPv6</b> &rarr; Edit <code>Default-IPv6</code> &rarr; <b>Path Monitor</b>.<br/>2. Check <b>Enable</b> &rarr; Target: <code>2001:4860:4860::8888</code>, Interval: <code>3</code>, Count: <code>5</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    # MODULE 7
    m7 = "Module 7: Enterprise IPv6 OSPFv3 Architecture"
    topics.append({
        'module': m7, 'num': 46, 'title': 'Advance-Routing: IPv6 OSPFv3 via GUI/CLI',
        'meaning': 'Enabling the OSPFv3 protocol daemon designed specifically for IPv6. Note that OSPFv3 still requires a 32-bit dotted-decimal Router-ID (e.g. 1.1.1.1).',
        'example': 'Enabling OSPFv3 on virtual router default with Router-ID 1.1.1.1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 enable yes router-id 1.1.1.1
admin@PA-VM# commit""",
        'gui': "1. Navigate to: <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> tab.<br/>2. Check <b>Enable</b> &rarr; Router ID: <code>1.1.1.1</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 47, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Basic and Multi-Area',
        'meaning': 'Configuring multi-area OSPFv3 topology. Links in Area 0 form the IPv6 backbone while Area 1 isolates branch networks.',
        'example': 'Placing ethernet1/1 in OSPFv3 Area 0.0.0.0 and ethernet1/2 in Area 0.0.0.1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.0 interface ethernet1/1 enable yes
admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.1 interface ethernet1/2 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; <b>Areas</b>.<br/>2. Add Area <code>0.0.0.0</code> (Interface: <code>ethernet1/1</code>) and Area <code>0.0.0.1</code> (Interface: <code>ethernet1/2</code>) &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 48, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Neighbor Table Verification',
        'meaning': 'Auditing OSPFv3 neighbor adjacencies. In OSPFv3, neighbors form adjacencies over IPv6 Link-Local addresses (fe80::) rather than global unicast addresses.',
        'example': 'Verifying neighbor status shows Full with peer link-local address fe80::ce1:c3ff:fe5e:0.',
        'cli': """admin@PA-VM> show routing protocol ospfv3 neighbor
admin@PA-VM> show routing protocol ospfv3 neighbor detail""",
        'gui': "1. Go to: <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>OSPFv3</b> &rarr; <b>Neighbors</b>.<br/>2. Confirm neighbor status shows <b>Full</b> over IPv6 link-local (fe80::) addresses."
    })

    topics.append({
        'module': m7, 'num': 49, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Database Table Verification',
        'meaning': 'Auditing the OSPFv3 Link-State Database (LSDB). Verifying Link LSAs (Type 8, flooding local link-local IPs) and Intra-Area-Prefix LSAs (Type 9, carrying IPv6 prefixes decoupled from topology).',
        'example': 'Running show routing protocol ospfv3 lsdb to verify Type 8 and Type 9 LSA synchronization.',
        'cli': """admin@PA-VM> show routing protocol ospfv3 lsdb
admin@PA-VM> show routing protocol ospfv3 dump""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>OSPFv3</b> &rarr; <b>Link State Database</b>.<br/>2. Audit Type 8 (Link) and Type 9 (Intra-Area-Prefix) LSA tables."
    })

    topics.append({
        'module': m7, 'num': 50, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Routing Table Verification',
        'meaning': 'Confirming computed OSPFv3 shortest paths installed into the active IPv6 forwarding table (FIB).',
        'example': 'Verifying learned IPv6 subnet 2001:db8:10::/64 installed with next-hop fe80::1 via ethernet1/1.',
        'cli': """admin@PA-VM> show routing protocol ospfv3 route
admin@PA-VM> show routing route protocol ospfv3 virtual-router default""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>Routing Table</b>.<br/>2. Filter for IPv6 routes learned via OSPFv3 to verify forwarding metrics."
    })

    topics.append({
        'module': m7, 'num': 51, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Virtual-Links',
        'meaning': 'Bridging a disconnected or partitioned IPv6 OSPFv3 area back to Area 0 across a transit area.',
        'example': 'Creating virtual link VL-IPv6-R3 across transit Area 1 to reach isolated router 3.3.3.3.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.1 virtual-link VL-IPv6-R3 neighbor-id 3.3.3.3 transit-area-id 0.0.0.1 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Area <code>0.0.0.1</code>.<br/>2. Select <b>Virtual Link</b> tab &rarr; Add <code>VL-IPv6-R3</code> &rarr; Neighbor: <code>3.3.3.3</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 52, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Hello Interval Modification',
        'meaning': 'Modifying the OSPFv3 Hello timer on an IPv6 interface to speed up link failure detection.',
        'example': 'Lowering Hello timer to 5s on interface ethernet1/1 in Area 0.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.0 interface ethernet1/1 hello-interval 5
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Area <code>0.0.0.0</code> &rarr; Click interface.<br/>2. Set <b>Hello Interval</b>: <code>5</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 53, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Dead Interval Modification',
        'meaning': 'Adjusting the OSPFv3 Dead timer (must match across peers) before dropping an unresponsive neighbor.',
        'example': 'Setting Dead timer to 20s (4x Hello timer of 5s) on ethernet1/1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.0 interface ethernet1/1 dead-counts 20
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Area <code>0.0.0.0</code> &rarr; Click interface.<br/>2. Set <b>Dead Interval</b>: <code>20</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 54, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Stub Area',
        'meaning': 'Configuring an IPv6 OSPF area to block external Type 5 LSAs, auto-injecting an IPv6 default route (::/0).',
        'example': 'Configuring branch Area 0.0.0.2 as Stub with default route metric 10.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.2 type stub default-route metric 10
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Add Area <code>0.0.0.2</code>.<br/>2. Type: <code>stub</code> &rarr; Default Route Metric: <code>10</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 55, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Totally Stub Area',
        'meaning': 'Blocking both External LSAs and Inter-Area Summary LSAs in IPv6, leaving only intra-area routes and a default route ::/0.',
        'example': 'Unchecking Accept Summary LSA on Area 0.0.0.2 to optimize branch memory.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.2 type stub accepts-summary-lsa no
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Area <code>0.0.0.2</code>.<br/>2. Type: <code>stub</code> &rarr; Uncheck <b>Accept Summary LSA</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 56, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Totally NSSA Area',
        'meaning': 'Permitting local IPv6 ASBR redistribution via Type 7 LSAs while blocking external Type 5 and summary Type 3 LSAs.',
        'example': 'Configuring Area 0.0.0.3 as Totally NSSA for a local dual-stack router.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.3 type nssa accepts-summary-lsa no
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Add Area <code>0.0.0.3</code>.<br/>2. Type: <code>nssa</code> &rarr; Uncheck <b>Accept Summary LSA</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 57, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-External Summarization',
        'meaning': 'Summarizing redistributed external IPv6 routes at the ASBR boundary into a single aggregate LSA.',
        'example': 'Summarizing external IPv6 subnets under 2001:db8::/32 at the firewall ASBR boundary.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 asbr-summary 2001:db8::/32 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; <b>ASBR Summary</b>.<br/>2. Add Prefix: <code>2001:db8::/32</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 58, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Inter-Area Summarization',
        'meaning': 'Summarizing internal IPv6 subnets at the ABR boundary into a single Type 3 Summary LSA advertised into Area 0.',
        'example': 'Aggregating branch /64 subnets under 2001:db8:1::/48 at the Area 1 border.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 area 0.0.0.1 range 2001:db8:1::/48 enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; Area <code>0.0.0.1</code>.<br/>2. Range tab &rarr; Add: <code>2001:db8:1::/48</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 59, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Default-Information-Originate',
        'meaning': 'Originating an IPv6 default route (::/0) into OSPFv3 so internal IPv6 nodes route outbound traffic through the firewall.',
        'example': 'Advertising default route ::/0 with metric 10 and metric-type ext-2 into OSPFv3.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 default-information-originate enable yes metric 10 metric-type ext-2
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; <b>Export Rules</b>.<br/>2. Check <b>Default Information Originate</b> &rarr; Metric: <code>10</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 60, 'title': 'Advance-Routing: IPv6 OSPFv3 Lab-Redistribution',
        'meaning': 'Injecting connected or static IPv6 routes into OSPFv3 via export rules.',
        'example': 'Redistributing local connected IPv6 subnets into OSPFv3 with metric 20.',
        'cli': """admin@PA-VM# set network virtual-router default protocol ospfv3 export-rules Redist-IPv6 enable yes metric 20
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>OSPFv3</b> &rarr; <b>Export Rules</b>.<br/>2. Add export rule referencing IPv6 redistribution profile &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m7, 'num': 61, 'title': 'Advance-Routing: IPv6 OSPFv3 Troubleshoot',
        'meaning': 'Diagnosing OSPFv3 issues including missing link-local addresses, IP protocol 89 drops, and MTU mismatches.',
        'example': 'Tailing routed.log to detect why an OSPFv3 neighbor is stuck in Init due to link-local fe80:: address unreachable.',
        'cli': """admin@PA-VM> show routing protocol ospfv3 status
admin@PA-VM> show routing protocol ospfv3 interface
admin@PA-VM> debug routing pfe ospfv3 all on
admin@PA-VM> tail follow yes mp-log routed.log""",
        'gui': "1. Go to: <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>System</b> &rarr; Filter: <code>(description contains 'ospfv3')</code>.<br/>2. Verify IPv6 link-local addressing on interfaces and check for security policy drops on protocol 89."
    })

    # MODULE 8
    m8 = "Module 8: Enterprise IPv6 Multiprotocol BGP (MP-BGP / BGPv6) Architecture"
    topics.append({
        'module': m8, 'num': 62, 'title': 'Advance-Routing: IPv6 BGPv6 via GUI/CLI',
        'meaning': 'Enabling the Multiprotocol BGP (MP-BGP) extension for IPv6 Address Family Identifier (AFI IPv6). Allows exchange of IPv6 Network Layer Reachability Information (NLRI).',
        'example': 'Activating BGP on virtual router default with local AS 65001 and configuring an external IPv6 peer in AS 65002.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp enable yes as 65001 router-id 1.1.1.1
admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-IPv6-ISP type external
admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-IPv6-ISP peer ISP-IPv6-Peer peer-as 65002 local-address ip 2001:db8:3::2/64 interface ethernet1/3 peer-address ip 2001:db8:3::1 enable yes address-family-identifier ipv6
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Peer Group</b> &rarr; Add <code>eBGP-IPv6-ISP</code>.<br/>2. Add Peer &rarr; Peer AS: <code>65002</code>, Peer IP: <code>2001:db8:3::1</code>, Address Family: <b>IPv6</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 63, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Basic',
        'meaning': 'Establishing and verifying an external IPv6 BGP peering session over TCP port 179.',
        'example': 'Activating the IPv6 BGP session to upstream telecom router 2001:db8:3::1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-IPv6-ISP peer ISP-IPv6-Peer enable yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select <code>ISP-IPv6-Peer</code>.<br/>2. Ensure <b>Enable</b> is checked &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 64, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Neighbor Table Verification',
        'meaning': 'Auditing the IPv6 BGP neighbor state to verify the session has reached Established status for Address Family IPv6.',
        'example': 'Checking show routing protocol bgp peer afi ipv6 to confirm 2001:db8:3::1 is Established.',
        'cli': """admin@PA-VM> show routing protocol bgp peer afi ipv6
admin@PA-VM> show routing protocol bgp summary""",
        'gui': "1. Go to: <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>BGP</b> &rarr; <b>Peer</b>.<br/>2. Confirm IPv6 neighbor shows Status = <b>Established</b>."
    })

    topics.append({
        'module': m8, 'num': 65, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-BGP Table Verification',
        'meaning': 'Inspecting the IPv6 Loc-RIB and Adj-RIB tables to evaluate received IPv6 prefixes, AS-Path, and next-hop reachability.',
        'example': 'Verifying learned prefix 2001:db8:30::/64 in Loc-RIB with AS-Path 65002.',
        'cli': """admin@PA-VM> show routing protocol bgp loc-rib afi ipv6
admin@PA-VM> show routing protocol bgp rib-out afi ipv6""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>BGP</b> &rarr; <b>Loc-RIB</b>.<br/>2. Select <b>IPv6</b> address family to inspect path attributes."
    })

    topics.append({
        'module': m8, 'num': 66, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Routing Table Verification',
        'meaning': 'Verifying best BGPv6 routes committed into the active IPv6 forwarding table with flag B.',
        'example': 'Confirming active IPv6 BGP route 2001:db8:30::/64 with next-hop 2001:db8:3::1 installed in the FIB.',
        'cli': """admin@PA-VM> show routing route protocol bgp ipv6-only yes virtual-router default""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <b>More Runtime Stats</b> &rarr; <b>Routing Table</b>.<br/>2. Filter for IPv6 and flag <b>B</b> to inspect committed next-hops."
    })

    topics.append({
        'module': m8, 'num': 67, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Next-Hop-Self',
        'meaning': 'Rewriting external IPv6 next-hop addresses to the firewall local IPv6 interface when advertising eBGP routes to internal iBGPv6 peers.',
        'example': 'Configuring Next-Hop-Self for internal peer Internal-Core-v6 so external IPv6 routes resolve to the firewall internal IPv6 address.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group iBGP-IPv6 peer Internal-Core-v6 next-hop use-self
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select iBGPv6 peer.<br/>2. In <i>Connection Options</i> &rarr; Next Hop: Select <b>Use Self</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 68, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Route-Reflector-Client',
        'meaning': 'Reflecting iBGPv6 routes between internal peers to eliminate the need for a full-mesh topology in large enterprise IPv6 networks.',
        'example': 'Designating Internal-Core-v6 as a Route Reflector Client under cluster-id 1.1.1.1.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group iBGP-IPv6 peer Internal-Core-v6 ref-client client
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select iBGPv6 peer.<br/>2. Reflector Client: Select <b>client</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 69, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Authentication',
        'meaning': 'Securing IPv6 BGP peering sessions using MD5 TCP checksums to block unauthorized session hijacking or spoofing.',
        'example': 'Configuring MD5 password IPv6BgpPass123! on IPv6 peering to ISP.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp peer-group eBGP-IPv6-ISP peer ISP-IPv6-Peer authentication md5 key IPv6BgpPass123!
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; Select IPv6 peer &rarr; <b>Authentication</b>.<br/>2. Type: <code>MD5</code> &rarr; Key: <code>IPv6BgpPass123!</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 70, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Aggregation',
        'meaning': 'Aggregating granular internal IPv6 subnets into a single /32 or /48 supernet advertisement to global transit providers while suppressing internal subnets.',
        'example': 'Aggregating enterprise IPv6 allocation under 2001:db8::/32 with summary-only enabled.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp aggregate-ipv6 2001:db8::/32 enable yes summary-only yes
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Aggregations (IPv6)</b>.<br/>2. Click <b>Add</b> &rarr; Prefix: <code>2001:db8::/32</code> &rarr; Check <b>Summary Only</b> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 71, 'title': 'Advance-Routing: IPv6 BGPv6 Lab-Redistribution',
        'meaning': 'Exporting corporate IPv6 prefixes (connected, static, or OSPFv3) into BGPv6 updates sent to upstream ISP transit routers.',
        'example': 'Exporting enterprise public prefix 2001:db8:1::/48 into BGPv6.',
        'cli': """admin@PA-VM# set network virtual-router default protocol bgp export-rules Export-IPv6-BGP enable yes match-address-prefix 2001:db8:1::/48
admin@PA-VM# commit""",
        'gui': "1. In <b>Virtual Routers</b> &rarr; <code>default</code> &rarr; <b>BGP</b> &rarr; <b>Export (IPv6)</b>.<br/>2. Add export rule matching enterprise prefix <code>2001:db8:1::/48</code> &rarr; <b>OK</b> &rarr; <b>Commit</b>."
    })

    topics.append({
        'module': m8, 'num': 72, 'title': 'Advance-Routing: IPv6 BGPv6 Troubleshoot',
        'meaning': 'Diagnosing IPv6 BGP peering failures: verifying TCP 179 connectivity over IPv6, ensuring security policy permits application bgp, resolving Address Family negotiation mismatches, and inspecting next-hop reachability.',
        'example': 'Tailing routed.log to detect AFI negotiation failures or link-local next-hop resolution issues with the upstream ISP.',
        'cli': """admin@PA-VM> show routing protocol bgp peer afi ipv6 detail
admin@PA-VM> show routing protocol bgp loc-rib afi ipv6
admin@PA-VM> debug routing pfe bgp all on
admin@PA-VM> tail follow yes mp-log routed.log""",
        'gui': "1. Go to: <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>System</b> &rarr; Filter: <code>(subtype eq routing) and (description contains 'bgp')</code>.<br/>2. Confirm IPv6 TCP 179 reachability; verify security policy allows application 'bgp' between peering zones."
    })

    return topics
