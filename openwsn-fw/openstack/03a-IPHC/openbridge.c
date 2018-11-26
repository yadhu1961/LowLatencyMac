#include "opendefs.h"
#include "openbridge.h"
#include "openserial.h"
#include "packetfunctions.h"
#include "iphc.h"
#include "idmanager.h"
#include "openqueue.h"

//=========================== variables =======================================

//=========================== prototypes ======================================
//=========================== public ==========================================

void openbridge_init() {
}

void openbridge_triggerData() {
   uint8_t           input_buffer[136];//worst case: 8B of next hop + 128B of data
   OpenQueueEntry_t* pkt;
   uint8_t           numDataBytes;
   numDataBytes = openserial_getInputBufferFilllevel();
  
    //poipoi xv
    //this is a temporal workaround as we are never supposed to get chunks of data
    //longer than input buffer size.. I assume that HDLC will solve that.
    // MAC header is 13B + 8 next hop so we cannot accept packets that are longer than 118B
    if (numDataBytes>(136 - 10/*21*/) || numDataBytes<8){
   //to prevent too short or too long serial frames to kill the stack  
       openserial_printError(COMPONENT_OPENBRIDGE,ERR_INPUTBUFFER_LENGTH,
                   (errorparameter_t)numDataBytes,
                   (errorparameter_t)0);
       return;
    }
    //copying the buffer once we know it is not too big
    openserial_getInputBuffer(&(input_buffer[0]),numDataBytes);
   //if (idmanager_getIsDAGroot()==TRUE && numDataBytes>0) {
    if (numDataBytes>0) {
      pkt = openqueue_getFreePacketBuffer(COMPONENT_OPENBRIDGE);
      if (pkt==NULL) {
         openserial_printError(COMPONENT_OPENBRIDGE,ERR_NO_FREE_PACKET_BUFFER,
                               (errorparameter_t)0,
                               (errorparameter_t)0);
         return;
      }
      //Yadhu added starts
      //openserial_printf(&input_buffer,numDataBytes,'D');
      //Just returning from here to test whether the uncorrupted packets are entering
      //openqueue_freePacketBuffer(pkt);
      //return;
      //Yadhu added ends
      //admin
      pkt->creator  = COMPONENT_OPENBRIDGE;
      pkt->owner    = COMPONENT_OPENBRIDGE;
      //l2
      pkt->l2_nextORpreviousHop.type = ADDR_64B;
      memcpy(&(pkt->l2_nextORpreviousHop.addr_64b[0]),&(input_buffer[0]),8);
      //payload
      packetfunctions_reserveHeaderSize(pkt,numDataBytes-8);
      memcpy(pkt->payload,&(input_buffer[8]),numDataBytes-8);

      // openserial_printf("payload",sizeof("payload"),'D');
      // openserial_printf(pkt->payload,pkt->length,'D');
      //this is to catch the too short packet. remove it after fw-103 is solved.
      // if (numDataBytes<16){ Not valid anymore, After reducing serial traffic
      //         openserial_printError(COMPONENT_OPENBRIDGE,ERR_INVALIDSERIALFRAME,
      //                       (errorparameter_t)0,
      //                       (errorparameter_t)0);
      // }
      //send
      opentimers_measure_ticks(0,0);
      if ((iphc_sendFromBridge(pkt))==E_FAIL) {
         openqueue_freePacketBuffer(pkt);
        leds_error_toggle();
      }
   }
}

void openbridge_sendDone(OpenQueueEntry_t* msg, owerror_t error) {
   msg->owner = COMPONENT_OPENBRIDGE;
   if (msg->creator!=COMPONENT_OPENBRIDGE) {
      openserial_printError(COMPONENT_OPENBRIDGE,ERR_UNEXPECTED_SENDDONE,
                            (errorparameter_t)0,
                            (errorparameter_t)0);
   }
   openqueue_freePacketBuffer(msg);
}

/**
\brief Receive a frame at the openbridge, which sends it out over serial.
*/
void openbridge_receive(OpenQueueEntry_t* msg) {
   //leds_error_toggle();
   // prepend previous hop
   //packetfunctions_reserveHeaderSize(msg,1);
   //memcpy(msg->payload,msg->l2_nextORpreviousHop.addr_64b,1);
   
   // prepend next hop (me), To reduce UART traffic assuming, DAGRoot knows its address.
   //packetfunctions_reserveHeaderSize(msg,LENGTH_ADDR64b);
   //memcpy(msg->payload,idmanager_getMyID(ADDR_64B)->addr_64b,LENGTH_ADDR64b);
   
   // send packet over serial (will be memcopied into serial buffer)
   openserial_printf((uint8_t*)(msg->payload),msg->length,'P');
   //leds_error_toggle();
   //openserial_printf("\r\n",2);
   
   // free packet
   openqueue_freePacketBuffer(msg);
}

//=========================== private =========================================
