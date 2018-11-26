#This module receives the payload which needs to injected to mote then prepares the 6LoWPAN packet

class UDPPacket:
    
    #These are default values
    d = {}
    
    d['tc']     = 0x0 #8bits
    d['fl']     = 0x0 #20 bits Setting flow label as zero always
    d['plen']   = 0x0 #16 bits
    d['nh']     = 17  #Indicates next header, i.e UDP 8bits
    d['hl']     = 0x40 # 8 bits hop limit
    #Default address values
    d['src']    = bytearray([0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0, 18, 75, 0, 6, 13, 155, 217])        #Source address 128 bits
    d['dst']    = bytearray([0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0, 18, 75, 0, 6, 21, 164, 137])     #Destination address
    
    #IPv6 payload, In otherwords UDP part
    d['sport']  = 59762 #Source port of UDP     2 bytes
    d['dport']  = 61618 #Destination port UDP   2 bytes
    d['len']    = 0x12  #UDP Payload Length     2 bytes
    d['chsum']  = 0x00  #Checksum this field is optional so making 0x00
    d['data']   = bytearray(['Y','a','d','h','u','n','a','n','d','a','n','a']) #UDP payload
    
    #In this function passed values are included in the UDP packet 
    def __init__(self,source=bytearray([0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0, 18, 75, 0, 6, 13, 155, 217]),
        dst=bytearray([0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0, 18, 75, 0, 6, 21, 164, 137]),
        sourceport=59762,dport=61618,data="Yadhunandana"):
            #update the dictionary values
            self.d['src'] = source
            self.d['dst'] = dst
            #Converting string to byte array
            tmp = bytearray()
            tmp.extend(data)
            
            self.d['data'] = tmp
            self.d['plen'] = len(self.d['data'])+8 #Data len, 2 bytes for each port number,2 bytes checksum,2 bytes length
            self.d['len'] = len(self.d['data'])+8
    
    def setData(self,data):
        
        tmp = bytearray()
        tmp.extend(data)
        self.d['data'] = tmp
        self.d['plen'] = len(self.d['data'])+8 #Data len, 2 bytes for each port number,2 bytes checksum,2 bytes length
        self.d['len'] = len(self.d['data'])+8
        
    def setSrc_and_Dest(self,source,dst):
        self.d['src'] = source
        self.d['dst'] = dst
        
    #This function converts dictionary values to bytearray returns that packet
    def getPacket(self):
        pktw = [((6 << 4) + (self.d['tc'] >> 4)),
                (((self.d['tc'] & 0x0F) << 4) + (self.d['fl'] >> 16)),
                ((self.d['fl'] >> 8) & 0x00FF),
                (self.d['fl'] & 0x0000FF),
                (self.d['plen'] >> 8),
                (self.d['plen'] & 0x00FF),
                (self.d['nh']),
                (self.d['hl'])]
        for i in range(0,16):
            pktw.append( (self.d['src'][i]) )
        for i in range(0,16):
            pktw.append( (self.d['dst'][i]) )
        pktw.append(self.d['sport'] >> 8 & 0x00FF)
        pktw.append(self.d['sport'] & 0x0000FF)
        pktw.append(self.d['dport'] >> 8 & 0x00FF)
        pktw.append(self.d['dport'] & 0x0000FF)
        pktw.append(self.d['len'] >> 8 & 0x00FF)
        pktw.append(self.d['len']   & 0x0000FF)
        pktw.append(self.d['chsum'])
        pktw.append(self.d['chsum'])
        
        for i in range(0,len(self.d['data'])):
            pktw.append( (self.d['data'][i]))
        
        return  pktw
        #udp_bytearray = ''.join([chr(c) for c in pktw])
        #test = bytearray()
        #test.extend(udp_bytearray)
        #return test
            
if __name__=="__main__":
    
    testUDP = UDPPacket()
    testUDP.getPacket()
