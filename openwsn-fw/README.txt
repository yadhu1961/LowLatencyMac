OpenWSN firmware: stuff that runs on a mote.

OpenWSN firmware modified/improved for achieving the low latency industrial communication.
(19 millisecond RTT is achieved. In addition to low RTT, modifications supporting multiloop
are also incorporated in the stack, currently supports only two loops with dagroot providing
only time synchronization, can be extended to arbitrary number of loops).

Author : Yadhunandana Rajathadripura Kumaraiah
Email  : yadhu.kumaraiah@tum.de

Functionalities implemented/improved in the stack.
(Only major modification details are explained. For minor details compare source OpenWSN source with opensource 
linux source code comparison tool "meld", believe me that's the best way to know everything :-).

1. Openserial driver redesign/optimization.
    To improve the speed of the serial communication baud rate is changed from 115200bps to 230400bps, This value
    is works perfectly with Z1-mote, However in openmote serial communication lot of data corruption is observed.
    In the process of openserial driver design new serial protocol is implemented to communicate between the host
    and the mote. This protocol has very low overhead compared to original protocol implementation. Two categories
    of packets are implemented for network management. Command type packets and Data type packets. Command type
    packets are used for setting the dagroot, changing the TSCH schedule, viewing the TSCH schedule, getting neigh
    -bors etc,(refer openserial.c for complete list). Data type commands are used for injecting packets to the mote.
    these two kind of packets type processing is done with separate modules (fancy word for independent functions)
    so the new functionalities can be added, means new packets types can be easily added. Whenever a command type
    packet is received mote processes the packet sends the response. For data type packets, packet which needs to 
    be injected is directly injected to the MAC layer queue through six top layer APIs.

2. Scheduling of the openserial driver.
    External MAC is a mechanism to decide when the data has to be sent from user application running in host to 
    the mote and vice versa. Since the mote has single microcontroller this communication time also should be 
    part of super frame schedule. In order to do that, serial communication timing is accommodated in the schedule
    through serial RX and serial TX slots. These slots are used for communicating with the host computer running
    user application. The mechanism is as explained below. In the schedule as soon serial RX slot starts, MAC layer
    calls the start input function of the openserial driver, then a request frame is sent to the host, to indicate
    that it is ready to receive. Once the host receives the request frame it sends the data to mote. In the original
    OpenWSN implementation, request frames were sent once in every super frame. In this design, user application
    cannot inject multiple data packets in one superframe although enough slots are available. This is not well 
    suited for achieving low latency communication. In our design the MAC layer is modified in such a way that for 
    every SERIALRX slot a request frame is sent to the host.

3. Increased the frequency of the frequency of beacon frames.
    Since the stack needs to support multiloops and beacon frames needs be transmitted or not is decided with some
    probability, It is necessary that all the nodes to receive synchronization packet within sync timeout. To avoid
    desynchronization frequency of the beacons frame is doubled. Channel 26 is used for sending beacon frames.

4. Modification to stack for directly copying received packets to serial buffer.
    Original design of the OpenWSN stack, whenever a packet is received it is pushed to receive queue. Sixtop layer
    processes the packet when there is idle time. When there is tight schedule, this idle time may not be immediate
    hence the packet has to wait in the buffer for more time. To achieve the low latency communication this design
    is modified to directly push the received paket to openserial buffer so that it can be immediately transmistted
    to host in the next available openserial TX slot. This reduced latency significantly.

5. Address assignment based on the command line parameter.
    Address assignment to the motes is not under the control of OpenWSN stack. It is part of the bsp of the platform.
    In OpenMote addresses are automatically assigned upon booting by the BSP. However this is not the case with Z1-
    Motes. Assignment of the addresses is done based on the command line parameter specified during the flashing of
    the firmware. In the current implementation five addresses are assigned to different motes based on the command
    line parameter specified. Same naming conventions are used in Python network management tool make sure they mat
    -ch with USB device nodes. In addition to address assignment these command line parameters are useful for condi
    -tional compilation of the code in the stack. Presently these condition compilations are used for deciding addr
    -ess, channel and the schedule. Future work would be to make implementation scalable for arbitrary number of
    nodes. Following list shows the command line parameters supported, corresponding addresses assigned and USB 
    device nodes they are connected to. This information is useful for flashing the firmware and to specify cmd
    line parameter to python network management tool.

    +--+-----------+---------------------------+--+----------------------------------------+
    |  | USB nodes |    command line parameter |  |             assigned address           |
    +--+-----------+---------------------------+--+----------------------------------------+
    |  | /dev/USB0 |    DG                     |  |   [0x14,0x15,0x92,0x00,0x00,0x00,0x01] |
    |  | /dev/USB1 |    LN1                    |  |   [0x14,0x15,0x92,0x00,0x00,0x00,0x02] |
    |  | /dev/USB2 |    LN2                    |  |   [0x14,0x15,0x92,0x00,0x00,0x00,0x03] |
    |  | /dev/USB3 |    LN3                    |  |   [0x14,0x15,0x92,0x00,0x00,0x00,0x04] |
    |  | /dev/USB4 |    LN4                    |  |   [0x14,0x15,0x92,0x00,0x00,0x00,0x05] |
    +--+-----------+---------------------------+--+----------------------------------------+


    Adderesses need to assigned as specified above to work with stack as it is. Otherwise modification to the stack
    and to the python network management module are needed. Name of the command line parameter designates the functi
    -nality of the mote. DG means it is a dagroot, LN means mote functions as leaf mote. Network functionality is 
    hard coded. Always LN1 forms a control loop with the LN2 and LN3 forms with LN4, It can be modified by changing 
    the channel used in the stack(static_schedule.c) and corresponding destination adresses in python NW management
    tool. More details about python NW management tool is explained in README.md in python code folder.

6. Optimization of OpenWSN slot frame, slot size and schedule.
    In the original OpenWSN slot size was 15ms and slot frame had 11 slots, Latency of the system was more than 100ms
    Industrial control systems need low latency. In an attempt to develop low latency testbed, OpenWSN stack is impro
    -ved/modified. The main components which were introducing latency were External MAC and Network MAC. With the 
    above explained modification to the openserial driver, External MAC latency is reduced. Next step was to optimize
    the MAC layer. After bottleneck and use case analysis, ACK part of the slot state machine is removed, Different 
    state time durations are reduced to bare minimum, After measuring exactly how much time is required for maximum
    packet size (i.e beacon packet size). Data packet size is less than beacon packet size in our setup. Slot size is
    agressively reduced from 15ms to 3.57ms. Further reduction is not possible unless the packet structure of beacon
    packet is modified. Future work would be modify the structure of Beacon packet structure to include the bare mini
    -mal information required for synchronization and remove the obvious fields such as network prefix and etc,.
    For exact size of different fields of the slot, please refer the source code.
    (openwsn-fw/bsp/boards/z1/board_info.h and openwsn-fw/openstack/02a-MAClow/IEEE802154E.h).

7. Sixtop MAC layer packet injection API's.
    To achieve low latency packets are injected directly to L2 from openserial driver. Original Openserial driver use 
    to inject packets to L4 (i.e UDP layer). To reduce the latency introduced by header fields of L3 and L4 and proce
    -ssing delay of the stack, Openserial driver injects packets directly to MAC layer. To facilitate packet injection
    to MAC layer new API sixtop_packet_inject() is added to sixtop layer. This API is called from openbridge.c 

8. Static schedule implementation and Improvement of schedule implementation.
    TSCH in OpenWSN is added dynamically after negotiating availability of the slots with the neibors. However this
    method tedious in a test setup and also in deterministic situations such as in industrial communication. To solve
    this problem and also to allow quick programming of the schedules to multiple nodes static schedule feature is
    implemented. In order to program the static schedule, User must decide schedule and add the corresponding info
    in static_schedule.c and shared slots in schedule.c. static_schedule.c file contains the schedule of the nodes in
    the network and they are separated by #ifdef statements. If you want to include new schedule include new #ifdef,
    and corresponding static schedule information in the static_schedule.c, shared slots in schedule.c, number of slots
    in schedule.h. In addition to schedule changes address assignment change also need to done in eui64.c.
    static_schedule.c contains information about offsets of TX and RX slots. TXRX, SRX and STX offsets are hardcoded in
    schedule.c file.

9. APIs to simultaneosly profile the code.
    Profiling of the code or operations in the code is very important for measuring how much time a particular function
    or api is taking. This profiled information is used for reducing the slot width to absolute minimum. To ease the
    measurements a extra api is added in opentimers.c "opentimers_measure_ticks" using this api simultaneouly two
    code profiling measurements can be taken. This function can be extended to arbitary number of simultaneos measurements.



How to flash the mote.
1. Due modification SConscript and SConstruct files new command line parameters are supported. These are choosed in the
    firware for preprocessor directives for conditional compilation, This command line parameters separate different device
    schedules.

    Command to flash a device.
    sudo scons board=z1 toolchain=mspgcc bootload=/dev/ttyUSB2 oos_openwsn device=LN2
    Addresses are assigned as explained in 5 point and corresponding table. presently values supported for device are DG, LN1
    LN2,LN3,LN4. Further additions can be done by modifying the Sconstruct file.