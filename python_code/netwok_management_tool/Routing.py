#This module includes the neccessary functions for maintaining the routing table,Parsing DAO's etc.


import time


class Routing():
    
    debug = False
    
    #Flags required for parsing the packet
    '''
    Class which is responsible for translating between 6LoWPAN and IPv6
    headers.

    This class implements the following RFCs:

    * *http://tools.ietf.org/html/rfc6282*
      Compression Format for IPv6 Datagrams over IEEE 802.15.4-Based Networks.
    * *http://tools.ietf.org/html/rfc2460*
      Internet Protocol, Version 6 (IPv6) Specification
    * *http://tools.ietf.org/html/draft-thubert-6man-flow-label-for-rpl-03
       The IPv6 Flow Label within a RPL domain
    '''
    #implementing http://tools.ietf.org/html/draft-thubert-6man-flow-label-for-rpl-03

    # http://www.iana.org/assignments/protocol-numbers/protocol-numbers.xml
    IANA_PROTOCOL_IPv6ROUTE  = 43
    IANA_UDP                 = 17
    IANA_ICMPv6              = 58
    IANA_IPv6HOPHEADER       = 0
    # there is no IANA for IPV6 HEADER right now, we use NHC identifier for it
    IPV6_HEADER              = 0xEE #https://tools.ietf.org/html/rfc6282#section-4.2

    #hop header flags
    O_FLAG                   = 0x10
    R_FLAG                   = 0x08
    F_FLAG                   = 0x04
    I_FLAG                   = 0x02
    K_FLAG                   = 0x01
    FLAG_MASK                = 0x1F

    #deadline hop header flags
    ORG_FLAG                 = 0x80
    DELAY_FLAG               = 0x40
    ETL_FLAG                 = 0x38
    OTL_FLAG                 = 0x07
    TU_FLAG                  = 0xC0
    EXP_FLAG                 = 0x38

    # Number of bytes in an IPv6 header.
    IPv6_HEADER_LEN          = 40

    IPHC_DISPATCH            = 3

    IPHC_TF_4B               = 0
    IPHC_TF_3B               = 1
    IPHC_TF_1B               = 2
    IPHC_TF_ELIDED           = 3

    IPHC_NH_INLINE           = 0
    IPHC_NH_COMPRESSED       = 1

    IPHC_HLIM_INLINE         = 0
    IPHC_HLIM_1              = 1
    IPHC_HLIM_64             = 2
    IPHC_HLIM_255            = 3

    IPHC_CID_NO              = 0
    IPHC_CID_YES             = 1

    IPHC_SAC_STATELESS       = 0
    IPHC_SAC_STATEFUL        = 1

    IPHC_SAM_128B            = 0
    IPHC_SAM_64B             = 1
    IPHC_SAM_16B             = 2
    IPHC_SAM_ELIDED          = 3

    IPHC_M_NO                = 0
    IPHC_M_YES               = 1

    IPHC_DAC_STATELESS       = 0
    IPHC_DAC_STATEFUL        = 1

    IPHC_DAM_128B            = 0
    IPHC_DAM_64B             = 1
    IPHC_DAM_16B             = 2
    IPHC_DAM_ELIDED          = 3

    NHC_DISPATCH             = 0x0E

    NHC_EID_MASK             = 0x0E
    NHC_EID_HOPBYHOP         = 0
    NHC_EID_ROUTING          = 1
    NHC_EID_IPV6             = 7

    NHC_NH_INLINE            = 0
    NHC_NH_COMPRESSED        = 1

    PAGE_ONE_DISPATCH        = 0xF1
    MASK_6LoRH               = 0xE0
    ELECTIVE_6LoRH           = 0xA0
    CRITICAL_6LoRH           = 0x80

    TYPE_6LoRH_DEADLINE      = 0x07
    TYPE_6LoRH_IP_IN_IP      = 0x06
    TYPE_6LoRH_RPI           = 0x05
    TYPE_6LoRH_RH3_0         = 0x00
    TYPE_6LoRH_RH3_1         = 0x01
    TYPE_6LoRH_RH3_2         = 0x02
    TYPE_6LoRH_RH3_3         = 0x03
    TYPE_6LoRH_RH3_4         = 0x04

    MASK_LENGTH_6LoRH_IPINIP = 0x1F

    #=== RPL source routing header (RFC6554)
    SR_FIR_TYPE              = 0x03

    #=== UDP Header compression (RFC6282)

    NHC_UDP_MASK             = 0xF8
    NHC_UDP_ID               = 0xF0
    NHC_UDP_PORTS_MASK       = 0x03

    NHC_UDP_PORTS_INLINE     = 0
    NHC_UDP_PORTS_16S_8D     = 1
    NHC_UDP_PORTS_8S_16D     = 2
    NHC_UDP_PORTS_4S_4D      = 3

    LINK_LOCAL_PREFIX        = [0xfe, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    
    
    
    _TARGET_INFORMATION_TYPE           = 0x05
    _TRANSIT_INFORMATION_TYPE          = 0x06
    
    def __init__(self):
        print "Routing instance created"
        self.state                = {}
        self.networkPrefix        = [0xbb,0xbb, 0, 0, 0, 0, 0, 0] #I have set this manually, However this is set by dispatcher in openvisualizer
        self.dagRootEui64         = None
        self.latencyStats         = {}
        
        #related to topology
        self.parents         = {}
        self.parentsLastSeen = {}
        self.NODE_TIMEOUT_THRESHOLD = 150
        
        
    def meshToLbr_notify(self,data):
        '''
        Converts a 6LowPAN packet into a IPv6 packet.

        This function dispatches the IPv6 packet with signal 'according to the destination address, protocol_type and port'.
        '''
        ipv6dic={}
        #build lowpan dictionary from the data
        ipv6dic = self.lowpan_to_ipv6(data)

        #read next header
        #print ipv6dic
        if ipv6dic['next_header']==self.IANA_IPv6HOPHEADER:
            #hop by hop header present, check flags and parse
            if (ipv6dic['hop_flags'] & self.O_FLAG) == self.O_FLAG:
                #error -- this packet has gone downstream somewhere.
                print "detected possible downstream link on upstream route from {0}".format(",".join(str(c) for c in ipv6dic['src_addr']))
            if (ipv6dic['hop_flags'] & self.R_FLAG) == self.R_FLAG:
                #error -- loop in the route
                print "detected possible loop on upstream route from {0}".format(",".join(str(c) for c in ipv6dic['src_addr']))
            #skip the header and process the rest of the message.
            ipv6dic['next_header'] = ipv6dic['hop_next_header']


        #===================================================================

        if ipv6dic['next_header']==self.IPV6_HEADER:
            #ipv6 header (inner)
            ipv6dic_inner = {}
            # parsing the iphc inner header and get the next_header
            ipv6dic_inner = self.lowpan_to_ipv6([ipv6dic['pre_hop'],ipv6dic['payload']])
            ipv6dic['next_header'] = ipv6dic_inner['next_header']
            ipv6dic['payload'] = ipv6dic_inner['payload']
            ipv6dic['payload_length'] = ipv6dic_inner['payload_length']
            ipv6dic['src_addr'] = ipv6dic_inner['src_addr']
            if not ipv6dic.has_key('hop_limit'):
                ipv6dic['hop_limit'] = ipv6dic_inner['hop_limit']
            ipv6dic['dst_addr'] = ipv6dic_inner['dst_addr']
            ipv6dic['flow_label'] = ipv6dic_inner['flow_label']

        if ipv6dic['next_header']==self.IANA_ICMPv6:
            #icmp header
            if len(ipv6dic['payload'])<5:
                print "wrong payload lenght on ICMPv6 packet {0}".format(",".join(str(c) for c in data))
                return

            ipv6dic['icmpv6_type']=ipv6dic['payload'][0]
            ipv6dic['icmpv6_code']=ipv6dic['payload'][1]
            ipv6dic['icmpv6_checksum']=ipv6dic['payload'][2:4]
            ipv6dic['app_payload']=ipv6dic['payload'][4:]

            #this function does the job
            #dispatchSignal=(tuple(ipv6dic['dst_addr']),self.PROTO_ICMPv6,ipv6dic['icmpv6_type'])
        elif ipv6dic['next_header']==self.IANA_UDP:
            print "UDP packet ipv6 format"
            #print ':'.join(str(hex(i)) for i in self.reassemble_ipv6_packet(ipv6dic))
            return (False,ipv6dic['payload'])
        #Only if the RPL type is RPL Control i.e first byte is 155, then only it is DAO otherwise it might echo reply
        #process only if the packet DAO
        if(ipv6dic['icmpv6_type'] == 0x9b):
            print " "
            print "======================================================="
            print "DAO message update parents"
        else:
            print "This icmp message is not DAO return from here"
            return (False,ipv6dic['payload'])
        
        #Calling api's related to RPL
        self._indicateDAO((ipv6dic['src_addr'],ipv6dic['app_payload']))
        return (True,ipv6dic['payload'])
        
    def lowpan_to_ipv6(self,data):

        pkt_ipv6 = {}
        mac_prev_hop=data[0]
        pkt_lowpan=data[1]
        
        if pkt_lowpan[0]==self.PAGE_ONE_DISPATCH:
            ptr = 1
            if pkt_lowpan[ptr] & self.MASK_6LoRH == self.CRITICAL_6LoRH and pkt_lowpan[ptr+1] == self.TYPE_6LoRH_RPI:
                # next header is RPI (hop by hop)
                pkt_ipv6['next_header'] = self.IANA_IPv6HOPHEADER
                pkt_ipv6['hop_flags'] = pkt_lowpan[ptr] & self.FLAG_MASK
                ptr = ptr+2

                if pkt_ipv6['hop_flags'] & self.I_FLAG==0:
                    pkt_ipv6['hop_rplInstanceID'] = pkt_lowpan[ptr]
                    ptr += 1
                else:
                    pkt_ipv6['hop_rplInstanceID'] = 0

                if pkt_ipv6['hop_flags'] & self.K_FLAG==0:
                    pkt_ipv6['hop_senderRank'] = ((pkt_lowpan[ptr]) << 8) + ((pkt_lowpan[ptr+1]) << 0)
                    ptr += 2
                else:
                    pkt_ipv6['hop_senderRank'] = (pkt_lowpan[ptr]) << 8
                    ptr += 1
                # iphc is following after hopbyhop header
                pkt_ipv6['hop_next_header'] = self.IPV6_HEADER

                if pkt_lowpan[ptr] & self.MASK_6LoRH == self.ELECTIVE_6LoRH and pkt_lowpan[ptr+1] == self.TYPE_6LoRH_IP_IN_IP:
                    # ip in ip encapsulation
                    length = pkt_lowpan[ptr] & self.MASK_LENGTH_6LoRH_IPINIP
                    pkt_ipv6['hop_limit'] = pkt_lowpan[ptr+2]
                    ptr += 3
                    if length == 1:
                        pkt_ipv6['src_addr'] = [0xbb,0xbb,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01]
                    elif length == 9:
                        pkt_ipv6['src_addr'] = self.networkPrefix + pkt_lowpan[ptr:ptr+8]
                        ptr += 8
                    elif length == 17:
                        pkt_ipv6['src_addr'] = pkt_lowpan[ptr:ptr+16]
                        ptr += 16
                    else:
                        print "ERROR wrong length of encapsulate"
                elif pkt_lowpan[ptr] & self.MASK_6LoRH == self.ELECTIVE_6LoRH and pkt_lowpan[ptr+1] == self.TYPE_6LoRH_DEADLINE:
                    length = pkt_lowpan[ptr] & self.MASK_LENGTH_6LoRH_IPINIP
                    nxt_byte = pkt_lowpan[ptr+2]

                    # 3rd byte
                    o_val = (pkt_lowpan[ptr+2] & self.ORG_FLAG) >> 7
                    d_val = (pkt_lowpan[ptr+2] & self.DELAY_FLAG) >> 6
                    etl_val = (pkt_lowpan[ptr+2] & self.ETL_FLAG) >> 3
                    otl_val = (pkt_lowpan[ptr+2] & self.OTL_FLAG)

                    # 4th byte
                    tu_val = (pkt_lowpan[ptr+3] & self.TU_FLAG) >> 6
                    exponent = (pkt_lowpan[ptr+3] & self.EXP_FLAG) >>  3

                    # Expiration Time
                    nxt_ptr = ptr+4
                    exp_time = []
                    for counter in range (0,etl_val+1):
                        exp_time.append(pkt_lowpan[nxt_ptr+counter])
                    e_time = exp_time[::-1]


                    # Origination Time
                    if o_val == 1:
                        org_time = []
                        nxt_ptr = nxt_ptr+counter+1
                        for counter in range (0,otl_val+1):
                            org_time.append(pkt_lowpan[nxt_ptr+counter])
                        o_time = org_time[::-1]

                    # log
                    if log.isEnabledFor(logging.ERROR):
                        output               = []
                        output              += [' ']
                        output              += ['Received a DeadLine Hop-by-Hop Header']
                        output              += ['exp_time is {0}'.format(u.formatAddr(e_time))]
                        if o_val == 1:
                            output              += ['org_time is {0}'.format(u.formatAddr(o_time))]
                        output               = '\n'.join(output)
                        log.error(output)
                        print output

                    ptr += length+1
            else:
                print "ERROR no support this type of 6LoRH yet"
        else:
            ptr = 2
            if (pkt_lowpan[0] >> 5) != 0x03:
                print "ERROR not a 6LowPAN packet"
                return

            # tf
            tf = ((pkt_lowpan[0]) >> 3) & 0x03
            if tf == self.IPHC_TF_3B:
                pkt_ipv6['flow_label'] = ((pkt_lowpan[ptr]) << 16) + ((pkt_lowpan[ptr+1]) << 8) + ((pkt_lowpan[ptr+2]) << 0)
                ptr = ptr + 3
            elif tf == self.IPHC_TF_ELIDED:
                pkt_ipv6['flow_label'] = 0
            else:
                print "Unsupported or wrong tf"
            # nh
            nh = ((pkt_lowpan[0]) >> 2) & 0x01
            if nh == self.IPHC_NH_INLINE:
                pkt_ipv6['next_header'] = (pkt_lowpan[ptr])
                ptr = ptr+1
            elif nh == self.IPHC_NH_COMPRESSED:
                # the next header will be retrieved later
                pass
            else:
                print "wrong nh field nh="+str(nh)

            # hlim
            hlim = (pkt_lowpan[0]) & 0x03
            if hlim == self.IPHC_HLIM_INLINE:
                pkt_ipv6['hop_limit'] = (pkt_lowpan[ptr])
                ptr = ptr+1
            elif hlim == self.IPHC_HLIM_1:
                pkt_ipv6['hop_limit'] = 1
            elif hlim == self.IPHC_HLIM_64:
                pkt_ipv6['hop_limit'] = 64
            elif hlim == self.IPHC_HLIM_255:
                pkt_ipv6['hop_limit'] = 255
            else:
                print "wrong hlim=="+str(hlim)

            # sac
            sac = ((pkt_lowpan[1]) >> 6) & 0x01
            if sac == self.IPHC_SAC_STATELESS:
                prefix = self.LINK_LOCAL_PREFIX
            elif sac == self.IPHC_SAC_STATEFUL:
                prefix = self.networkPrefix

            # sam
            sam = ((pkt_lowpan[1]) >> 4) & 0x03
            if sam == self.IPHC_SAM_ELIDED:
                #pkt from the previous hop
                pkt_ipv6['src_addr'] = prefix + mac_prev_hop

            elif sam == self.IPHC_SAM_16B:
                a1 = pkt_lowpan[ptr]
                a2 = pkt_lowpan[ptr+1]
                ptr = ptr+2
                s = ''.join(['\x00','\x00','\x00','\x00','\x00','\x00',a1,a2])
                pkt_ipv6['src_addr'] = prefix+s

            elif sam == self.IPHC_SAM_64B:
                pkt_ipv6['src_addr'] = prefix+pkt_lowpan[ptr:ptr+8]
                ptr = ptr + 8
            elif sam == self.IPHC_SAM_128B:
                pkt_ipv6['src_addr'] = pkt_lowpan[ptr:ptr+16]
                ptr = ptr + 16
            else:
                print "wrong sam=="+str(sam)

            # dac
            dac = ((pkt_lowpan[1]) >> 2) & 0x01
            if dac == self.IPHC_DAC_STATELESS:
                prefix = self.LINK_LOCAL_PREFIX
            elif dac == self.IPHC_DAC_STATEFUL:
                prefix = self.networkPrefix

            # dam
            dam = ((pkt_lowpan[1]) & 0x03)
            if dam == self.IPHC_DAM_ELIDED:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("IPHC_DAM_ELIDED this packet is for the dagroot!")
                pkt_ipv6['dst_addr'] = prefix+self.dagRootEui64
            elif dam == self.IPHC_DAM_16B:
                a1 = pkt_lowpan[ptr]
                a2 = pkt_lowpan[ptr+1]
                ptr = ptr+2
                s = ''.join(['\x00','\x00','\x00','\x00','\x00','\x00',a1,a2])
                pkt_ipv6['dst_addr'] = prefix+s
            elif dam == self.IPHC_DAM_64B:
                pkt_ipv6['dst_addr'] = prefix+pkt_lowpan[ptr:ptr+8]
                ptr = ptr + 8
            elif dam == self.IPHC_DAM_128B:
                pkt_ipv6['dst_addr'] = pkt_lowpan[ptr:ptr+16]
                ptr = ptr + 16
            else:
                log.error("wrong dam=="+str(dam))

            if nh == self.IPHC_NH_COMPRESSED:
                if ((pkt_lowpan[ptr] >> 4) & 0x0f) == self.NHC_DISPATCH:
                    eid = (pkt_lowpan[ptr] & self.NHC_EID_MASK) >> 1
                    if eid == self.NHC_EID_HOPBYHOP:
                        pkt_ipv6['next_header'] = self.IANA_IPv6HOPHEADER
                    elif eid == self.NHC_EID_IPV6:
                        pkt_ipv6['next_header'] = self.IPV6_HEADER
                    else:
                        log.error("wrong NH_EID=="+str(eid))
                elif pkt_lowpan[ptr] & self.NHC_UDP_ID == self.NHC_UDP_ID:
                    pkt_ipv6['next_header'] = self.IANA_UDP

            #hop by hop header
            #composed of NHC, NextHeader,Len + Rpl Option
            if pkt_ipv6['next_header'] == self.IANA_IPv6HOPHEADER:
                 pkt_ipv6['hop_nhc'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 if (pkt_ipv6['hop_nhc'] & 0x01) == 0:
                    pkt_ipv6['hop_next_header'] = pkt_lowpan[ptr]
                    ptr = ptr+1
                 else :
                    # the next header filed will be elided
                    pass
                 pkt_ipv6['hop_hdr_len'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 #start of RPL Option
                 pkt_ipv6['hop_optionType'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 pkt_ipv6['hop_optionLen'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 pkt_ipv6['hop_flags'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 pkt_ipv6['hop_rplInstanceID'] = pkt_lowpan[ptr]
                 ptr = ptr+1
                 pkt_ipv6['hop_senderRank'] = ((pkt_lowpan[ptr]) << 8) + ((pkt_lowpan[ptr+1]) << 0)
                 ptr = ptr+2
                 #end RPL option
                 if (pkt_ipv6['hop_nhc'] & 0x01) == 1:
                     if ((pkt_lowpan[ptr]>>1) & 0x07) == self.NHC_EID_IPV6:
                         pkt_ipv6['hop_next_header'] = self.IPV6_HEADER

        # payload
        pkt_ipv6['version']        = 6
        pkt_ipv6['traffic_class']  = 0
        pkt_ipv6['payload']        = pkt_lowpan[ptr:len(pkt_lowpan)]

        pkt_ipv6['payload_length'] = len(pkt_ipv6['payload'])
        pkt_ipv6['pre_hop']        = mac_prev_hop
        return pkt_ipv6
        
        
    def _indicateDAO(self,tup):
        '''
        Indicate a new DAO was received.
        
        This function parses the received packet, and if valid, updates the
        information needed to compute source routes.
        '''
        # retrieve source and destination
        try:
            source                = tup[0]
            if len(source)>8: 
                source=source[len(source)-8:]
            dao                   = tup[1]
        except IndexError:
            print "DAO too short, no space for destination and source"
            return
        
        if self.debug:
            a=":".join(hex(c) for c in source)
            output                = []
            output               += ['received DAO:']
            output               += ['- source :      '+a]
            a = ":".join(hex(c) for c in dao)
            output               += ['- dao :         '+a]
            output                = '\n'.join(output)
            print output
        
        # retrieve DAO header
        dao_header                = {}
        dao_transit_information   = {}
        dao_target_information    = {}
        
        try:
            # RPL header
            dao_header['RPL_InstanceID']    = dao[0]
            dao_header['RPL_flags']         = dao[1]
            dao_header['RPL_Reserved']      = dao[2]
            dao_header['RPL_DAO_Sequence']  = dao[3]
            # DODAGID
            dao_header['DODAGID']           = dao[4:20]
           
            dao                             = dao[20:]
            # retrieve transit information header and parents
            parents                         = []
            children                        = []
            #print "from : "+':'.join([hex(i) for i in source])
            #print ":".join(hex(i) for i in dao)
            while len(dao)>0:
                if   dao[0]==self._TRANSIT_INFORMATION_TYPE:
                    if(source[7] == 0x03):
                        print "dao: "+':'.join([hex(i) for i in dao])
                    # transit information option
                    dao_transit_information['Transit_information_type']             = dao[0]
                    dao_transit_information['Transit_information_length']           = dao[1]
                    dao_transit_information['Transit_information_flags']            = dao[2]
                    dao_transit_information['Transit_information_path_control']     = dao[3]
                    dao_transit_information['Transit_information_path_sequence']    = dao[4]
                    #print hex(dao[4])
                    dao_transit_information['Transit_information_path_lifetime']    = dao[5]
                    # address of the parent
                    prefix        =  dao[6:14]
                    parents      += [dao[14:22]]
                    dao           = dao[22:]
                elif dao[0]==self._TARGET_INFORMATION_TYPE:
                    if(source[7] == 0x03):
                        print "dao: "+':'.join([hex(i) for i in dao])
                    dao_target_information['Target_information_type']               = dao[0]
                    dao_target_information['Target_information_length']             = dao[1]
                    dao_target_information['Target_information_flags']              = dao[2]
                    dao_target_information['Target_information_prefix_length']      = dao[3]
                    # address of the child
                    prefix        =  dao[4:12]
                    children     += [dao[12:20]]
                    dao           = dao[20:]
                else:
                    print "DAO with wrong Option {0}. Neither Transit nor Target."
                    return
        except IndexError:
            print "DAO too short ({0} bytes), no space for DAO header"
            return
        
        if self.debug:
            print "RPL_InstanceID:                      "+str(dao_header['RPL_InstanceID'])
            print "RPL_flags:                           "+str(dao_header['RPL_flags'])
            print "RPL_Reserved:                        "+str(dao_header['RPL_Reserved'])
            print "RPL_DAO_Sequence:                    "+str(dao_header['RPL_DAO_Sequence'])
            print 'Transit_information_type:            '+str(dao_transit_information['Transit_information_type'])
            print 'Transit_information_length:          '+str(dao_transit_information['Transit_information_length'])
            print 'Transit_information_flags:           '+str(dao_transit_information['Transit_information_flags'])
            print 'Transit_information_path_control:    '+str(dao_transit_information['Transit_information_path_control'])
            print 'Transit_information_path_sequence:   '+str(dao_transit_information['Transit_information_path_sequence'])
            print 'Transit_information_path_lifetime:   '+str(dao_transit_information['Transit_information_path_lifetime'])
        
        # if you get here, the DAO was parsed correctly
        #Need to call functions build topology by updating parents after every DAO
        self.updateParents((tuple(source),parents))

        
    def updateParents(self,data):
        ''' inserts parent information into the parents dictionary '''
        self.parents.update({data[0]:data[1]})
        self.parentsLastSeen.update({data[0]: time.time()})
        
        print self.parents
        
        print "updated parents clearing the list based on last seen"
        print "======================================================="
        print " "
        self.clearNodeTimeout()
        
    def getParents(self):
        return self.parents
        
    def clearNodeTimeout(self):
        threshold = time.time() - self.NODE_TIMEOUT_THRESHOLD
        for node in self.parentsLastSeen.keys():
            if self.parentsLastSeen[node] < threshold:
                if node in self.parents:
                    del self.parents[node]
                del self.parentsLastSeen[node]
                
    def convert_to_iphc(self,data):
            
            ipv6_bytes       = data

            # turn raw byte into dictionary of fields
            ipv6             = self.disassemble_ipv6(ipv6_bytes)

             # filter out multicast packets
            if ipv6['dst_addr'][0]==0xff:
                return

            if ipv6['dst_addr'][0]==0xfe and ipv6['dst_addr'][1]==0x80:
                isLinkLocal = True
            else:
                isLinkLocal = False

            # log
            #if log.isEnabledFor(logging.DEBUG):
                #log.debug(self._format_IPv6(ipv6,ipv6_bytes))

            # convert IPv6 dictionary into 6LoWPAN dictionary
            lowpan           = self.ipv6_to_lowpan(ipv6)

            # add the source route to this destination
            if len(lowpan['dst_addr'])==16:
                dst_addr=lowpan['dst_addr'][8:]
            elif len(lowpan['dst_addr'])==8:
                dst_addr=lowpan['dst_addr']
            else:
                dst_addr=None
                print 'unsupported address format {0}'.format(lowpan['dst_addr'])

            if isLinkLocal:
                lowpan['route'] = [dst_addr]
            else:
                lowpan['route'] = self.getSourceRoute(dst_addr)

                if len(lowpan['route'])<2:
                    # no source route could be found
                    print ':'.join(hex(i) for i in lowpan['dst_addr'])
                    print "no source route found"
                    # TODO: return ICMPv6 message
                    return

                lowpan['route'].pop() #remove last as this is me.

            lowpan['nextHop'] = lowpan['route'][len(lowpan['route'])-1] #get next hop as this has to be the destination address, this is the last element on the list
            
            # turn dictionary of fields into raw bytes
            lowpan_bytes     = self.reassemble_lowpan(lowpan)

            return (lowpan['nextHop'],lowpan_bytes)
            # log
            #if log.isEnabledFor(logging.DEBUG):
        
        
    def disassemble_ipv6(self,ipv6):
        '''
        Turn byte array representing IPv6 packets into into dictionary
        of fields.

        See http://tools.ietf.org/html/rfc2460#page-4.

        :param ipv6: [in] Byte array representing an IPv6 packet.

        :raises: ValueError when some part of the process is not defined in
            the standard.
        :raises: NotImplementedError when some part of the process is defined in
            the standard, but not implemented in this module.

        :returns: A dictionary of fields.
        '''
        if len(ipv6)<self.IPv6_HEADER_LEN:
            raise ValueError('Packet too small ({0} bytes) no space for IPv6 header'.format(len(ipv6)))

        returnVal                      = {}
        returnVal['version']           = ipv6[0] >> 4
        if returnVal['version']!=6:
            raise ValueError('Not an IPv6 packet, version=={0}'.format(returnVal['version']))

        returnVal['traffic_class']     = ((ipv6[0] & 0x0F) << 4) + (ipv6[1] >> 4)
        returnVal['flow_label']        = ((ipv6[1] & 0x0F) << 16) + (ipv6[2] << 8) + ipv6[3]
        returnVal['payload_length']    = self.buf2int(ipv6[4:6])
        returnVal['next_header']       = ipv6[6]
        returnVal['hop_limit']         = ipv6[7]
        returnVal['src_addr']          = ipv6[8:8+16]
        returnVal['dst_addr']          = ipv6[24:24+16]
        returnVal['payload']           = ipv6[40:]

        return returnVal
        
    def buf2int(self,buf):
        '''
        Converts some consecutive bytes of a buffer into an integer. 
        Big-endianness is assumed.
        
        :param buf:      [in] Byte array.
        '''
        returnVal = 0
        for i in range(len(buf)):
            returnVal += buf[i]<<(8*(len(buf)-i-1))
        return returnVal
        
    def ipv6_to_lowpan(self,ipv6):
        '''
        Compact IPv6 header into 6LowPAN header.

        :param ipv6: [in] A disassembled IPv6 packet.

        :raises: ValueError when some part of the process is not defined in
            the standard.
        :raises: NotImplementedError when some part of the process is defined in
            the standard, but not implemented in this module.

        :returns: A disassembled 6LoWPAN packet.
        '''

        # header
        lowpan = {}

        # tf
        if ipv6['traffic_class']!=0:
            raise NotImplementedError('traffic_class={0} unsupported'.format(ipv6['traffic_class']))
        # comment the flow_label check as it's zero in 6lowpan network. See follow RFC:
        # https://tools.ietf.org/html/rfc4944#section-10.1
        # if ipv6['flow_label']!=0:
            # raise NotImplementedError('flow_label={0} unsupported'.format(ipv6['flow_label']))
        lowpan['tf']         = []

        # nh
        lowpan['nh']         = [ipv6['next_header']]

        # hlim
        lowpan['hlim']       = [ipv6['hop_limit']]

        # cid
        lowpan['cid']        = []

        # src_addr
        lowpan['src_addr']   = ipv6['src_addr']

        # dst_addr
        lowpan['dst_addr']   = ipv6['dst_addr']

        # payload
        lowpan['payload']    = ipv6['payload']

        # join
        return lowpan
        
        
    def getSourceRoute(self,destAddr):
        '''
        Retrieve the source route to a given mote.
        
        :param destAddr: [in] The EUI64 address of the final destination.
        
        :returns: The source route, a list of EUI64 address, ordered from
            destination to source.
        '''
        
        sourceRoute = []
        try:
            parents=self.getParents()
            self.getSourceRoute_internal(destAddr,sourceRoute,parents)
        except Exception as err:
            print err
            raise
        
        return sourceRoute
    def getSourceRoute_internal(self,destAddr,sourceRoute,parents):
        
        if not destAddr:
            # no more parents
            return
        
        if not parents.get(tuple(destAddr)):
            # this node does not have a list of parents
            return
        
        # first time add destination address
        if destAddr not in sourceRoute:
            sourceRoute     += [destAddr]
        
        # pick a parent
        parent               = parents.get(tuple(destAddr))[0]
        
        # avoid loops
        if parent not in sourceRoute:
            sourceRoute     += [parent]
            
            # add non empty parents recursively
            nextparent       = self.getSourceRoute_internal(parent,sourceRoute,parents)
            
            if nextparent:
                sourceRoute += [nextparent]

    def reassemble_lowpan(self,lowpan):
        '''
        Turn dictionary of 6LoWPAN header fields into byte array.

        :param lowpan: [in] dictionary of fields representing a 6LoWPAN header.

        :returns: A list of bytes representing the 6LoWPAN packet.
        '''
        returnVal            = []

        # the 6lowpan packet contains 4 parts
        # 1. Page Dispatch (page 1)
        # 2. RH3 6LoRH(s)
        # 3. RPI 6LoRH (maybe elided)
        # 4. IPinIP 6LoRH (maybe elided)
        # 5. IPHC inner header

        # ===================== 1. Page Dispatch (page 1) =====================

        returnVal += [self.PAGE_ONE_DISPATCH]

        if lowpan['src_addr'][:8] != [187, 187, 0, 0, 0, 0, 0, 0]:
            compressReference = [187, 187, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        else:
            compressReference = lowpan['src_addr']


        # destination address
        if len(lowpan['route'])>1:
            # source route needed, get prefix from compression Reference
            if len(compressReference)==16:
                prefix=compressReference[:8]

            # =======================3. RH3 6LoRH(s) ==============================
            sizeUnitType = 0xff
            size     = 0
            hopList  = []

            for hop in list(reversed(lowpan['route'][1:])):
                size += 1
                if compressReference[-8:-1] == hop[-8:-1]:
                    if sizeUnitType != 0xff:
                        if  sizeUnitType != self.TYPE_6LoRH_RH3_0:
                            returnVal += [self.CRITICAL_6LoRH|(size-2),sizeUnitType]
                            returnVal += hopList
                            size = 1
                            sizeUnitType = self.TYPE_6LoRH_RH3_0
                            hopList = [hop[-1]]
                            compressReference = hop
                        else:
                            hopList += [hop[-1]]
                            compressReference = hop
                    else:
                        sizeUnitType = self.TYPE_6LoRH_RH3_0
                        hopList += [hop[-1]]
                        compressReference = hop
                elif compressReference[-8:-2] == hop[-8:-2]:
                    if sizeUnitType != 0xff:
                        if  sizeUnitType != self.TYPE_6LoRH_RH3_1:
                            returnVal += [self.CRITICAL_6LoRH|(size-2),sizeUnitType]
                            returnVal += hopList
                            size = 1
                            sizeUnitType = self.TYPE_6LoRH_RH3_1
                            hopList = hop[-2:]
                            compressReference = hop
                        else:
                            hopList += hop[-2:]
                            compressReference = hop
                    else:
                        sizeUnitType = self.TYPE_6LoRH_RH3_1
                        hopList += hop[-2:]
                        compressReference = hop
                elif compressReference[-8:-4] == hop[-8:-4]:
                    if sizeUnitType != 0xff:
                        if  sizeUnitType != self.TYPE_6LoRH_RH3_2:
                            returnVal += [self.CRITICAL_6LoRH|(size-2),sizeUnitType]
                            returnVal += hopList
                            size = 1
                            sizeUnitType = self.TYPE_6LoRH_RH3_2
                            hopList = hop[-4:]
                            compressReference = hop
                        else:
                            hopList += hop[-4:]
                            compressReference = hop
                    else:
                        sizeUnitType = self.TYPE_6LoRH_RH3_2
                        hopList += hop[-4:]
                        compressReference = hop
                else:
                    if sizeUnitType != 0xff:
                        if  sizeUnitType != self.TYPE_6LoRH_RH3_3:
                            returnVal += [self.CRITICAL_6LoRH|(size-2),sizeUnitType]
                            returnVal += hopList
                            size = 1
                            sizeUnitType = self.TYPE_6LoRH_RH3_3
                            hopList = hop
                            compressReference = hop
                        else:
                            hopList += hop
                            compressReference = hop
                    else:
                        sizeUnitType = self.TYPE_6LoRH_RH3_3
                        hopList += hop
                        compressReference = hop

            returnVal += [self.CRITICAL_6LoRH|(size-1),sizeUnitType]
            returnVal += hopList

        # ===================== 2. IPinIP 6LoRH ===============================

        if lowpan['src_addr'][:8] != [187, 187, 0, 0, 0, 0, 0, 0]:
            # add RPI
            # TBD
            flag = self.O_FLAG | self.I_FLAG | self.K_FLAG
            senderRank = 0 # rank of dagroot
            returnVal += [self.CRITICAL_6LoRH | flag,self.TYPE_6LoRH_RPI,senderRank]
            # ip in ip 6lorh
            l = 1
            returnVal += [self.ELECTIVE_6LoRH | l,self.TYPE_6LoRH_IP_IN_IP]
            returnVal += lowpan['hlim']

            compressReference = [187, 187, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        else:
            compressReference = lowpan['src_addr']

        # ========================= 4. IPHC inner header ======================
        # Byte1: 011(3b) TF(2b) NH(1b) HLIM(2b)
        if len(lowpan['tf'])==0:
            tf               = self.IPHC_TF_ELIDED
        else:
            raise NotImplementedError()
        # next header is in NHC format
        nh               = self.IPHC_NH_INLINE
        if   lowpan['hlim'][0]==1:
            hlim             = self.IPHC_HLIM_1
            lowpan['hlim'] = []
        elif lowpan['hlim'][0]==64:
            hlim             = self.IPHC_HLIM_64
            lowpan['hlim'] = []
        elif lowpan['hlim'][0]==255:
            hlim             = self.IPHC_HLIM_255
            lowpan['hlim'] = []
        else:
            hlim             = self.IPHC_HLIM_INLINE
        returnVal           += [(self.IPHC_DISPATCH<<5) + (tf<<3) + (nh<<2) + (hlim<<0)]

        # Byte2: CID(1b) SAC(1b) SAM(2b) M(1b) DAC(2b) DAM(2b)
        if len(lowpan['cid'])==0:
            cid              = self.IPHC_CID_NO
        else:
            cid              = self.IPHC_CID_YES

        if self._isLinkLocal(lowpan['src_addr']):
            sac                  = self.IPHC_SAC_STATELESS
            lowpan['src_addr'] = lowpan['src_addr'][8:]
        else:
            sac                  = self.IPHC_SAC_STATEFUL
            if lowpan['src_addr'][:8] == [187, 187, 0, 0, 0, 0, 0, 0]:
                lowpan['src_addr'] = lowpan['src_addr'][8:]

        if   len(lowpan['src_addr'])==128/8:
            sam              = self.IPHC_SAM_128B
        elif len(lowpan['src_addr'])==64/8:
            sam              = self.IPHC_SAM_64B
        elif len(lowpan['src_addr'])==16/8:
            sam              = self.IPHC_SAM_16B
        elif len(lowpan['src_addr'])==0:
            sam              = self.IPHC_SAM_ELIDED
        else:
            raise SystemError()

        if self._isLinkLocal(lowpan['dst_addr']):
            dac                  = self.IPHC_DAC_STATELESS
            lowpan['dst_addr'] = lowpan['dst_addr'][8:]
        else:
            dac                  = self.IPHC_DAC_STATEFUL
            if lowpan['dst_addr'][:8] == [187, 187, 0, 0, 0, 0, 0, 0]:
                lowpan['dst_addr'] = lowpan['dst_addr'][8:]

        m                    = self.IPHC_M_NO
        if   len(lowpan['dst_addr'])==128/8:
            dam              = self.IPHC_DAM_128B
        elif len(lowpan['dst_addr'])==64/8:
            dam              = self.IPHC_DAM_64B
        elif len(lowpan['dst_addr'])==16/8:
            dam              = self.IPHC_DAM_16B
        elif len(lowpan['dst_addr'])==0:
            dam              = self.IPHC_DAM_ELIDED
        else:
            raise SystemError()
        returnVal           += [(cid << 7) + (sac << 6) + (sam << 4) + (m << 3) + (dac << 2) + (dam << 0)]

        # tf
        returnVal           += lowpan['tf']

        # nh
        returnVal           += lowpan['nh']

        # hlim
        returnVal           += lowpan['hlim']

        # cid
        returnVal           += lowpan['cid']

        # src_addr
        returnVal           += lowpan['src_addr']

        # dst_addr
        returnVal           += lowpan['dst_addr']

        # payload
        returnVal           += lowpan['payload']

        return returnVal
        
    def _isLinkLocal(self, ipv6Address):
        if ipv6Address[:8] == self.LINK_LOCAL_PREFIX:
            return True
        return False

    def reassemble_ipv6_packet(self, pkt):
        pktw = [((6 << 4) + (pkt['traffic_class'] >> 4)),
                (((pkt['traffic_class'] & 0x0F) << 4) + (pkt['flow_label'] >> 16)),
                ((pkt['flow_label'] >> 8) & 0x00FF),
                (pkt['flow_label'] & 0x0000FF),
                (pkt['payload_length'] >> 8),
                (pkt['payload_length'] & 0x00FF),
                (pkt['next_header']),
                (pkt['hop_limit'])]
        for i in range(0,16):
            pktw.append( (pkt['src_addr'][i]) )
        for i in range(0,16):
            pktw.append( (pkt['dst_addr'][i]) )

        return pktw + pkt['payload']





















