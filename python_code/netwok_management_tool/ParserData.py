# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License


class ParserData():
    
    debug = False
    
    def __init__(self):
        print "__init__ function"
        #Empty function for now
    
    
    #======================== public ==========================================
    
    def parseInput(self,input):
        #print input
        if self.debug:
            a=":".join(hex(c) for c in input)
            print "input data "+a
        
        #source and destination of the message
        #dest = input[0:8]
        
        #source is elided!!! so it is not there.. check that.
        source = input[0:8]
        if self.debug:
            a=":".join(hex(c) for c in dest)
            print "destination address of the packet is {0} "+a
        if self.debug:
            a=":".join(hex(c) for c in source)
            print "source address (just previous hop) of the packet is {0} "+a
        
        input = input[8:]
        if self.debug:
            a=":".join(hex(c) for c in input)
            print "packet without source,dest and asn: "+a
        return (source, input)
