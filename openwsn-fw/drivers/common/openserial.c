/**
\brief Definition of the "custom openserial" driver.

\author Fabien Chraim <chraim@eecs.berkeley.edu>, March 2012.
\author Thomas Watteyne <thomas.watteyne@inria.fr>, August 2016.
*/

#include "opendefs.h"
#include "openserial.h"
#include "IEEE802154E.h"
#include "neighbors.h"
#include "sixtop.h"
#include "icmpv6echo.h"
#include "idmanager.h"
#include "openqueue.h"
#include "openbridge.h"
#include "leds.h"
#include "schedule.h"
#include "uart.h"
#include "opentimers.h"
#include "openhdlc.h"
#include "schedule.h"
#include "icmpv6rpl.h"
#include "icmpv6echo.h"
#include "sf0.h"
#include "stdint.h"
#include "scheduler.h" //Added for accessing scheduler API's

//Local function declarations
uint8_t circular_buffer_push(circBuf_t *,uint8_t );

uint8_t circular_buffer_pop(circBuf_t *,uint8_t *);

uint8_t openserial_handleCommands(void);

uint8_t handle_control_commands(void);

uint8_t handle_data_commands(void);

uint8_t inject_packet(void);

uint8_t send_response_packet(uint8_t *,uint8_t);

void udp_inject_sendDone(OpenQueueEntry_t* msg, owerror_t error);

void udp_inject_receive(OpenQueueEntry_t* msg);

bool verify_checksum();

// misc
void openserial_board_reset_cb(opentimers_id_t id);

/**
 * {These values define the command types}
 */
enum control_commands
{
    SET_DAG_ROOT = 0,
    GET_NODE_TYPE,          //This is to check whether the node is dagroot or not, This will be useful for python code.
    GET_NEIGHBORS_COUNT,
    GET_NEIGHBORS,
    GET_SCHEDULE,
    ADD_TX_SLOT,
    ADD_RX_SLOT,
    DUMP_RADIO_PACKETS,
    RESET_BOARD
};

enum data_commands 
{
    INJECT_UDP_PACKET = 0,
    INJECT_TCP_PACKET
};

static const uint8_t packet_dst_addr[]   = {
   0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
   0, 18, 75, 0, 6, 21, 164, 137
};

/*
 * Local variables (Variables used within this file)
 */
//Structure useful for measuring the delays in the stack
typedef struct {
   uint16_t  required_ticks;
   uint8_t received_bytes;
   uint8_t packet_len;
} ticks_measure_vars_t;

openserial_vars_t openserial_vars;

uint16_t serial_packet_loss_counter = 0;

//Defining transmission buffer for the uart.
CIRCBUF_DEF(tx_buffer,SERIAL_OUTPUT_BUFFER_SIZE);

//Receiving buffer for the uart.
CIRCBUF_DEF(rx_buffer,SERIAL_INPUT_BUFFER_SIZE);

udp_inject_vars_t udp_inject_vars;

bool isPacket = FALSE;

//Received byte count, For measuring the time taken to receive a frame serially
//ticks_measure_vars_t ticks_measure_vars;
//=========================== public ==========================================

//===== admin

void openserial_init() {

    memset(&openserial_vars,0,sizeof(openserial_vars_t));
    // clear local variables
    memset(&udp_inject_vars,0,sizeof(udp_inject_vars_t));
    //memset(&ticks_measure_vars,0,sizeof(ticks_measure_vars_t));

    openserial_vars.reqFrame[0] = START_FLAG;
    openserial_vars.reqFrame[1] = 0x02;             //Length of request frame
    openserial_vars.reqFrame[2] = REQUEST_FRAME;    //This byte indicates request frame
    openserial_vars.reqFrameIdx = 0;                //Pointer to request frame bytes sent

    // set callbacks
    uart_setCallbacks(
        isr_openserial_tx,
        isr_openserial_rx
    );

    // register at UDP stack
    udp_inject_vars.desc.port              = WKP_UDP_OPENSERIAL;
    udp_inject_vars.desc.callbackReceive   = &udp_inject_receive;
    udp_inject_vars.desc.callbackSendDone  = &udp_inject_sendDone;
    openudp_register(&udp_inject_vars.desc);
}

//===== scheduling

/**
 * @brief      {This function, for every 8 slots(function called after every 8 slots)
 *              reads contents of the received buffer then takes action according to 
 *              the received command}
 */
void openserial_startInput(uint8_t asn,uint16_t schedule_offset) {

    INTERRUPT_DECLARATION();
    uart_clearTxInterrupts();
    uart_clearRxInterrupts();      // clear possible pending interrupts
    uart_enableInterrupts();       // Enable USCI_A1 TX & RX interrupt
    DISABLE_INTERRUPTS();

    openserial_vars.busy_tx = FALSE;
    openserial_vars.bytes_transmitted = 0;
    openserial_vars.tx_pkt_len = 0;

    openserial_vars.reqFrameIdx    = 0;
    openserial_vars.mode = MODE_INPUT;

    uart_writeByte(openserial_vars.reqFrame[openserial_vars.reqFrameIdx]);
    ENABLE_INTERRUPTS();
    //ticks_measure_vars.required_ticks = sctimer_readCounter();
}

void openserial_startOutput(uint8_t asn,uint16_t schedule_offset) {

    uint8_t data = NULL;
    uint16_t buffer_level = 0;
    INTERRUPT_DECLARATION();
    //=== flush TX buffer,
    uart_clearTxInterrupts();
    uart_clearRxInterrupts();          // clear possible pending interrupts
    uart_enableInterrupts();           // Enable USCI_A1 TX & RX interrupt

    DISABLE_INTERRUPTS();
    buffer_level = tx_buffer.fill_level;
    ENABLE_INTERRUPTS();

    if(tx_buffer.buffer[tx_buffer.tail+1] < buffer_level && buffer_level > 0)
    {
        if(isPacket)
        {
            uint8_t temp[3] = {asn,CELLTYPE_OFF,0xff & schedule_offset };
            //openserial_printf(&temp,3,'D');
            isPacket = FALSE;
        }
        DISABLE_INTERRUPTS();
        openserial_vars.mode = MODE_OUTPUT;
        if(!circular_buffer_pop(&tx_buffer,&data))
            leds_error_toggle();
        openserial_vars.busy_tx = TRUE;
        openserial_vars.bytes_transmitted = 1;
        openserial_vars.total_bytes_transmitted = 1;
        openserial_vars.tx_pkt_len = tx_buffer.buffer[tx_buffer.tail];//tail here, not tail+1, since 0x7e is already popped
        // if(isPacket)
        // {
        //     uint16_t ticks = opentimers_measure_ticks(0,1);
        //     openserial_printf(&ticks,2,'D');
        //     isPacket = FALSE;
        // }
        uart_writeByte(data);
        ENABLE_INTERRUPTS();
    }
}

void openserial_stop() {
    uint16_t buffer_level;

    INTERRUPT_DECLARATION();
    DISABLE_INTERRUPTS();
    buffer_level = rx_buffer.fill_level;
    ENABLE_INTERRUPTS();

    // disable UART interrupts
    uart_disableInterrupts();

    DISABLE_INTERRUPTS();
    openserial_vars.mode = MODE_OFF;
    ENABLE_INTERRUPTS();

    if(buffer_level > SERIAL_INPUT_BUFFER_SIZE-1)
        openserial_printError(COMPONENT_OPENSERIAL,ERR_INPUT_BUFFER_OVERFLOW,(errorparameter_t)rx_buffer.maxLen,(errorparameter_t)rx_buffer.fill_level);

    if(START_FLAG == rx_buffer.buffer[rx_buffer.tail])
        circular_buffer_pop(&rx_buffer,NULL);
    if(buffer_level > rx_buffer.buffer[rx_buffer.tail])
    {
        //openserial_printf(ticks_measure_vars.required_ticks,4,'D'); //This is to check the time taken for receiving the packet by uart
        //Here I am going to check the checksum, If its correct then only I process the command else throw away the frame
        if(verify_checksum())
            openserial_handleCommands();
    }
    DISABLE_INTERRUPTS();
    //Resetting the buffer
    rx_buffer.head = rx_buffer.tail = 0;
    rx_buffer.fill_level = 0;
    ENABLE_INTERRUPTS();
    //Clearing the stats of previous serial packet
    //memset(&ticks_measure_vars,0,sizeof(ticks_measure_vars_t));
    return;
}

bool verify_checksum() {
    uint16_t calc_chsum,frame_chsum;
    uint8_t idx = 0;
    calc_chsum = rx_buffer.buffer[rx_buffer.tail];
    for(idx = 1;idx<rx_buffer.buffer[rx_buffer.tail]-2;idx++)
        calc_chsum += rx_buffer.buffer[rx_buffer.tail+idx];
    memcpy(&frame_chsum,&rx_buffer.buffer[rx_buffer.buffer[rx_buffer.tail]-1],2);
     if(calc_chsum != frame_chsum)
     {
        serial_packet_loss_counter++;
        openserial_printf(&serial_packet_loss_counter,2,SERIAL_MSG_ERR);
         return FALSE;
     }
    return TRUE;
}

/**
 * @brief      {This function is added for logging purpose, prints the message to the serial port}
 *
 * @param      data_ptr  The data pointer
 * @param[in]  data_len  The data length
 *
 * @return     { description_of_the_return_value }
 */
uint8_t openserial_printf(char *data_ptr , uint8_t data_len,uint8_t type) {
    uint8_t idx;
    INTERRUPT_DECLARATION();

    DISABLE_INTERRUPTS();

    if(type == 'P')
        isPacket = TRUE;

    if(!circular_buffer_push(&tx_buffer,START_FLAG))
        leds_error_on();

    if(!circular_buffer_push(&tx_buffer,data_len+2)) //+2 because we include type of message byte and length byte as part of the packet
        leds_error_on();

    if(!circular_buffer_push(&tx_buffer,type)) //+1 because we include type of message byte as part of the packet
        leds_error_on();

    //Here i am going to fill the tx_buffer which will be eventually printed to serial terminal.
    for(idx = 0 ;idx < data_len; idx++)
    {
        if(!circular_buffer_push(&tx_buffer,data_ptr[idx]))
        {
            leds_error_on();
            break; //Signifies that ring buffer is full, break the loop
        }
    }

    ENABLE_INTERRUPTS();
    return idx-1; // returning number of bytes printed.
}

uint8_t openserial_handleCommands(void) {
    uint8_t cmdByte;
    cmdByte = rx_buffer.buffer[rx_buffer.tail+1];
    if(cmdByte == CONTROL_COMMAND)
        handle_control_commands();
    else if(cmdByte == DATA_COMMAND)
        handle_data_commands();
}

uint8_t handle_control_commands() {
    uint8_t nbr_count,index,nbr_list[40],slots[10] = {0,0,0,0,0,0,0,0,0,0},node_type = FALSE,slotframeID,control_cmd_byte;
    uint16_t maxActiveSlots = 0,i = 0;
    bool     foundNeighbor;
    neighborRow_t* neighbor;
    open_addr_t nbr;
    scheduleEntry_t* sE;
    opentimers_id_t id;
    uint32_t  reference;
    cellInfo_ht  celllist_add[CELLLIST_MAX_LEN];
    control_cmd_byte = rx_buffer.buffer[rx_buffer.tail+2];
    switch(control_cmd_byte)
    {
        case SET_DAG_ROOT:             //0 corresponds to set dagroot command.
            idmanager_triggerAboutRoot();
            break;
        case GET_NODE_TYPE:             //1 corresponds to get node type 1 means dagroot, zero means normal mote
            node_type = idmanager_getIsDAGroot();
            send_response_packet(&node_type,1);
            break;
        case GET_NEIGHBORS_COUNT:
            nbr_count = neighbors_getNumNeighbors();
            send_response_packet(&nbr_count,1);
            break;
        case GET_NEIGHBORS:
            nbr_count = neighbors_getNumNeighbors();
            for(index = 0;index < nbr_count;index++)
            {
                if (neighbors_getInfo(index, &neighbor) != FALSE)
                    memcpy(nbr_list+index*8,&neighbor->addr_64b.addr_64b,8);
            }
            send_response_packet(nbr_list,nbr_count*8);
            break;
        case GET_SCHEDULE:
            maxActiveSlots = schedule_getMaxActiveSlots();
            slotframeID = schedule_getFrameHandle();
            for(i = 0;i<maxActiveSlots;i++)
            {

                if (schedule_getInfo((uint8_t)i, &sE) == E_FAIL)
                {
                    openserial_printf("schedule error",sizeof("schedule error")-1,SERIAL_MSG_ERR);
                    return E_FAIL;
                }
                else
                {
                    if(sE->type == CELLTYPE_TX) {
                        slots[1] = sE->slotOffset;
                        slots[0]++;
                    }
                    else if(sE->type == CELLTYPE_RX) {
                        slots[3] = sE->slotOffset;
                        slots[2]++;
                    }
                    else if(sE->type == CELLTYPE_TXRX) {
                        slots[5] = sE->slotOffset;
                        slots[4]++;
                    }
                    else if(sE->type == CELLTYPE_SERIALRX) {
                        slots[7] = sE->slotOffset;
                        slots[6]++;
                    }
                    else if(sE->type == CELLTYPE_OFF) {
                        slots[9] = sE->slotOffset; //No need to worry about slotoffset of off slot
                        slots[8]++;
                    }
                }
            }
            send_response_packet(slots,10);
            break;
        case ADD_TX_SLOT:
            //foundNeighbor = icmpv6rpl_getPreferredParentEui64(&nbr);
            foundNeighbor = neighbors_getInfo(0, &neighbor); //Index is zero since we have only one neighbor
            //neighbor nout found
            if (foundNeighbor==FALSE)
            {
                return E_FAIL;
            }
            memcpy(&(nbr.addr_64b),&neighbor->addr_64b.addr_64b,8);
            nbr.type = ADDR_64B;
            if (sixtop_setHandler(SIX_HANDLER_SF0)==FALSE)
            {
                leds_error_toggle();
                return E_FAIL;
            }

            //To check whether the slots available
            if(sf0_candidateAddCellList(celllist_add,1)==FALSE)
            {
                leds_error_toggle();
                return E_FAIL;
            }

            sixtop_request(
                IANA_6TOP_CMD_ADD,                  // code
                &nbr,                          // neighbor
                1,                                  // number cells
                LINKOPTIONS_TX,                     // cellOptions
                celllist_add,                       // celllist to add
                NULL,                               // celllist to delete (not used)
                sf0_getsfid(),                      // sfid
                0,                                  // list command offset (not used)
                0                                   // list command maximum celllist (not used)
            );
            break;
        case ADD_RX_SLOT:
            //foundNeighbor = icmpv6rpl_getPreferredParentEui64(&nbr);
            foundNeighbor = neighbors_getInfo(0, &neighbor); //Index is zero since we have only one neighbor
            //neighbor nout found
            if (foundNeighbor==FALSE)
            {
                return E_FAIL;
            }
            memcpy(&(nbr.addr_64b),&neighbor->addr_64b.addr_64b,8);

            nbr.type = ADDR_64B; //Very important to specify this

            if (sixtop_setHandler(SIX_HANDLER_SF0)==FALSE)
            {
                leds_error_toggle();
                return E_FAIL;
            }

            //To check whether the slots available
            if(sf0_candidateAddCellList(celllist_add,1)==FALSE)
            {
                leds_error_toggle();
                return E_FAIL;
            }

            sixtop_request(
                IANA_6TOP_CMD_ADD,                  // code
                &nbr,                          // neighbor
                1,                                  // number cells
                LINKOPTIONS_RX,                     // cellOptions
                celllist_add,                       // celllist to add
                NULL,                               // celllist to delete (not used)
                sf0_getsfid(),                      // sfid
                0,                                  // list command offset (not used)
                0                                   // list command maximum celllist (not used)
            );
            break;
        case RESET_BOARD:
            id        = opentimers_create();
            reference = opentimers_getValue();
            opentimers_scheduleAbsolute(
                id,                             // timerId
                1000,                          // duration
                reference,                      // reference
                TIME_MS,                        // timetype
                openserial_board_reset_cb       // callback
                );
            break;
    }
}

uint8_t handle_data_commands() {
    uint8_t data_cmd_byte;
    data_cmd_byte = rx_buffer.buffer[rx_buffer.tail+2];
    switch(data_cmd_byte)
    {
        case 0:         //0 corresponds to UDP packet so inject udp packet
        inject_packet();
        break;
    }
}

uint8_t send_response_packet(uint8_t *data,uint8_t length)
{
    uint8_t resp[50] = {0};
    //In this first byte takes into account length byte, command category, command sub category,length of result
    resp[0] = rx_buffer.buffer[rx_buffer.tail+1];
    resp[1] = rx_buffer.buffer[rx_buffer.tail+2];
    memcpy(resp+2,data,length);
    openserial_printf(resp,length+2,SERIAL_MSG_RSP); //resp[0] contains the length of the packet
}


uint8_t inject_packet()
{
    OpenQueueEntry_t*    pkt;
    // don't run if not synch
    if (ieee154e_isSynch() == FALSE) return;

    //This is because, since only mac layer is running in DAGroot udp_send always fails so
    //just return from here.
    //if (idmanager_getIsDAGroot()) {
        //Here I have to call openbridge to inject packet and packet has to be in iphc format.
        openbridge_triggerData();
     //   return;
    //}
    //Now start forming the udp packet.
    // get a free packet buffer.
    // pkt = openqueue_getFreePacketBuffer(COMPONENT_OPENSERIAL);
    // if (pkt == NULL) {
    //     openserial_printError(COMPONENT_OPENSERIAL,ERR_NO_FREE_PACKET_BUFFER,
    //                (errorparameter_t)0,
    //                (errorparameter_t)0);
    //     return;
    // }
    // pkt->owner                         = COMPONENT_OPENSERIAL;
    // pkt->creator                       = COMPONENT_OPENSERIAL;
    // pkt->l4_protocol                   = IANA_UDP;
    // pkt->l4_destination_port           = WKP_UDP_OPENSERIAL;
    // pkt->l4_sourcePortORicmpv6Type     = WKP_UDP_OPENSERIAL;
    // pkt->l3_destinationAdd.type        = ADDR_128B;
    // memcpy(&pkt->l3_destinationAdd.addr_128b[0],packet_dst_addr,16);

    // packetfunctions_reserveHeaderSize(pkt,rx_buffer.buffer[rx_buffer.tail]-5);
    // int tmp=rx_buffer.buffer[rx_buffer.tail]-5;
    // memcpy(&pkt->payload[0],&rx_buffer.buffer[rx_buffer.tail]+3,rx_buffer.buffer[rx_buffer.tail]-5);
    // //leds_error_toggle();
    // //opentimers_measure_ticks(0,0);//start the measurement
    // if ((openudp_send(pkt))==E_FAIL) {
    //     openqueue_freePacketBuffer(pkt);
    //     openserial_printError(COMPONENT_OPENSERIAL,ERR_PKT_INJECT_FAILED,
    //                (errorparameter_t)0,
    //                (errorparameter_t)0);
    // }
}

void udp_inject_sendDone(OpenQueueEntry_t* msg, owerror_t error) {
    uint8_t buff[] = {7,7,7,7,7};
    //openserial_printf(buff,sizeof(buff),SERIAL_MSG_DEB);
    openqueue_freePacketBuffer(msg);
}

void udp_inject_receive(OpenQueueEntry_t* pkt) {
    uint8_t buff[] = {8,8,8,8,8};
    //openserial_printf(buff,sizeof(buff),SERIAL_MSG_DEB);
    //openserial_printf(&pkt->payload[0],pkt->length,SERIAL_MSG_PKT);
    openqueue_freePacketBuffer(pkt);
}

//===== retrieving inputBuffer for openbridge packet inject

uint8_t openserial_getInputBufferFilllevel()
{
    //Subratracting 5 in length for three commnd bytes(0x73,cmdbyte,subcmdbyte,checksum)
    return rx_buffer.buffer[rx_buffer.tail]-5;
}

uint8_t openserial_getInputBuffer(uint8_t* bufferToWrite, uint8_t maxNumBytes)
{
    //openserial_printf(openserial_vars.reqFrame+3,openserial_vars.reqFrame[0]-3,'D');
    //Subratracting 5 in length for three commnd bytes(0x73,cmdbyte,subcmdbyte,checksum)
    memcpy(bufferToWrite,&rx_buffer.buffer[rx_buffer.tail]+3,rx_buffer.buffer[rx_buffer.tail]-5);
    return rx_buffer.buffer[rx_buffer.tail]-5;
}

//=========================== interrupt handlers ==============================

/**
 * { this function gets called once the tx of byte is completed, Executed in isr
 *  useful for writing the next byte of data to the tx buffer
 *  executed in ISR, called from scheduler.c}
 */
void isr_openserial_tx() {
    uint8_t bytes = 0;
    switch (openserial_vars.mode)
    {
        case MODE_INPUT:
            openserial_vars.reqFrameIdx++;
            if (openserial_vars.reqFrameIdx<sizeof(openserial_vars.reqFrame))
                uart_writeByte(openserial_vars.reqFrame[openserial_vars.reqFrameIdx]);
            break;
        case MODE_OUTPUT:
             //This means one pkt tx is finished. +1 to to take 0x7E in to account.
            if(openserial_vars.bytes_transmitted == openserial_vars.tx_pkt_len+1)
            {
                //leds_error_toggle();
                //  //This means enough bytes are present in the buffer, Also check buffer has sum values.
                if(tx_buffer.buffer[tx_buffer.tail+1] > tx_buffer.fill_level && tx_buffer.fill_level > 0)// && \
                    //This logic to check whether we will be able to finish this packet in this slot
                    //openserial_vars.total_bytes_transmitted+tx_buffer.buffer[tx_buffer.tail+1] < 120)
                {
                    if(!circular_buffer_pop(&tx_buffer,&bytes))
                        leds_error_toggle();
                    openserial_vars.busy_tx = TRUE;
                    openserial_vars.bytes_transmitted = 1;
                    openserial_vars.tx_pkt_len = tx_buffer.buffer[tx_buffer.tail+1];
                    uart_writeByte(bytes);
                    return;
                }
                else
                {
                    openserial_vars.busy_tx = FALSE;
                    openserial_vars.mode = MODE_OFF;
                    openserial_vars.bytes_transmitted = 0;
                    openserial_vars.total_bytes_transmitted = 0;
                    return;
                }
            }
            if(!circular_buffer_pop(&tx_buffer,&bytes))
                leds_error_toggle();
            uart_writeByte(bytes);
            openserial_vars.bytes_transmitted++;
            openserial_vars.total_bytes_transmitted++;
            break;
        case MODE_OFF:
            default:
            break;
    }
}

/**
 * { this function gets called when uart has received a byte, Executed in isr context
 *  useful for reading data from rxbuf
 *  executed in ISR, called from scheduler.c}
 */
void isr_openserial_rx() {
    // uint32_t ticks;
    // stop if I'm not in input mode
    if (openserial_vars.mode!=MODE_INPUT)
        return;
    //ticks = opentimers_getValue() - ticks_measure_vars.required_ticks;
    //openserial_printf(&ticks,4,'D');
    uint8_t data = uart_readByte();
    //Measurement code starts here
    //ticks_measure_vars.received_bytes++;
    //  if(data == START_FLAG)
    // {
    //      ticks_measure_vars.required_ticks = sctimer_readCounter();
    //     //openserial_printf(&ticks_measure_vars.required_ticks,4,'D');
    // }
    // if(ticks_measure_vars.received_bytes == 2) //2 Because second byte contains the length byte.
    // {
    //     ticks_measure_vars.packet_len = data;
    // }
    // else if(ticks_measure_vars.received_bytes == ticks_measure_vars.packet_len + 1 && ticks_measure_vars.packet_len)
    // {
    //     //These ticks are for packet_len-1 bytes, Because we started considering ticks after first byte is received
    //     ticks_measure_vars.required_ticks = sctimer_readCounter() - ticks_measure_vars.required_ticks;
    //     openserial_printf(&ticks_measure_vars.required_ticks,2,'D');
    //     leds_error_toggle();
    // }
    //Measurement code ends here
    circular_buffer_push(&rx_buffer,data);
}

/**
 * @brief      { adds the data to the circular buffer,Made inline to improve the performance in the expense of code size }
 *
 * @param      buffer_ptr  The buffer pointer
 * @param[in]  dataValue   The data value
 *
 * @return     { TRUE if value is successfully pushed to the buffer, FALSE otherwise }
 */
port_INLINE uint8_t circular_buffer_push(circBuf_t *buffer_ptr,uint8_t dataValue)
{
    uint8_t next = buffer_ptr->head + 1;

    if(next >= buffer_ptr->maxLen)
        next = 0;
    //This signifies that ring buffer is full, Hence blink error led and log the error
    if(next == buffer_ptr->tail)
    {
        if(buffer_ptr == &rx_buffer)
            openserial_printError(COMPONENT_OPENSERIAL,ERR_INPUT_BUFFER_OVERFLOW, \
                (errorparameter_t)0,(errorparameter_t)buffer_ptr->fill_level);
        else
            openserial_printError(COMPONENT_OPENSERIAL,ERR_OUTPUT_BUFFER_OVERFLOW,\
                (errorparameter_t)1,(errorparameter_t)tx_buffer.fill_level);
        leds_error_on();
        return FALSE;
    }
    buffer_ptr->buffer[buffer_ptr->head] = dataValue;
    buffer_ptr->head = next;
    buffer_ptr->fill_level++;
    return TRUE;
}

/**
 * @brief      { reading a value from the circular buffer,,Made inline to improve the performance in the expense of code size}
 *
 * @param      buffer_ptr  The buffer pointer.
 * @param      data        The data pointer points to the address where read data will be copied.
 *
 * @return     { TRUE if value is successfully read from the buffer, FALSE otherwise }
 */
port_INLINE uint8_t circular_buffer_pop(circBuf_t *buffer_ptr,uint8_t *data)
{
    uint8_t next;
    // if the head isn't ahead of the tail, we don't have any characters
    if (buffer_ptr->head == buffer_ptr->tail)       // check if circular buffer is empty.
        return FALSE;                               // and return with an error.

    next = buffer_ptr->tail + 1;
    if(next >= buffer_ptr->maxLen)
        next = 0;

    if(data != NULL)
        *data = buffer_ptr->buffer[buffer_ptr->tail]; // Read data and then move

    buffer_ptr->tail = next;
    buffer_ptr->fill_level--;
    return TRUE;
}

// printing
owerror_t openserial_printError(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    uint8_t buff[] = {0,0,0,0,0,0};
    buff[0] = calling_component;
    buff[1] = error_code;
    memcpy(buff+2,&arg1,2);
    memcpy(buff+4,&arg2,2);
    //openserial_printf(buff,6,SERIAL_MSG_ERR);
    return E_SUCCESS;
}

//Unused prototypes of functions.
//=========================== prototypes ======================================

owerror_t openserial_printInfoErrorCritical(
    char             severity,
    uint8_t          calling_component,
    uint8_t          error_code,
    errorparameter_t arg1,
    errorparameter_t arg2
);

// command handlers
void openserial_handleEcho(uint8_t* but, uint8_t bufLen);
void openserial_get6pInfo(uint8_t commandId, uint8_t* code,uint8_t* cellOptions,uint8_t* numCells,cellInfo_ht* celllist_add,cellInfo_ht* celllist_delete,uint8_t* listOffset,uint8_t* maxListLen,uint8_t ptr, uint8_t commandLen);


// HDLC output
void outputHdlcOpen(void);
void outputHdlcWrite(uint8_t b);
void outputHdlcClose(void);

// HDLC input
void inputHdlcOpen(void);
void inputHdlcWrite(uint8_t b);
void inputHdlcClose(void);

// sniffer
void sniffer_setListeningChannel(uint8_t channel);


/***************************************************************************************/
/* 
 * 
 * 
 * Only stubs, here onwards
 * 
 * 
 */
/**************************************************************************************/

void openserial_register(openserial_rsvpt* rsvp) {
    //stub
}

//===== printing

owerror_t openserial_printStatus(
    uint8_t             statusElement,
    uint8_t*            buffer,
    uint8_t             length
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printInfo(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printCritical(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printData(uint8_t* buffer, uint8_t length) {
    //Disabled
    return E_SUCCESS;
}

owerror_t openserial_printSniffedPacket(uint8_t* buffer, uint8_t length, uint8_t channel) {
    //Disabled
    return E_SUCCESS;
}

//===== debugprint

/**
\brief Trigger this module to print status information, over serial.

debugPrint_* functions are used by the openserial module to continuously print
status information about several modules in the OpenWSN stack.

\returns TRUE if this function printed something, FALSE otherwise.
*/
bool debugPrint_outBufferIndexes() {

    return TRUE;
}

//=========================== private =========================================

//===== printing

owerror_t openserial_printInfoErrorCritical(
    char             severity,
    uint8_t          calling_component,
    uint8_t          error_code,
    errorparameter_t arg1,
    errorparameter_t arg2
) {
    return E_SUCCESS;
}

//===== command handlers

void openserial_handleEcho(uint8_t* buf, uint8_t bufLen){
    // echo back what you received
    openserial_printData(
        buf,
        bufLen
    );
}

void openserial_get6pInfo(uint8_t commandId, uint8_t* code,uint8_t* cellOptions,uint8_t* numCells,cellInfo_ht* celllist_add,cellInfo_ht* celllist_delete,uint8_t* listOffset,uint8_t* maxListLen,uint8_t ptr, uint8_t commandLen){
    //Stubs function;
}

//===== misc

void openserial_board_reset_cb(opentimers_id_t id) {
    board_reset();
}

//===== hdlc (output)

/**
\brief Start an HDLC frame in the output buffer.
*/
port_INLINE void outputHdlcOpen() {

}
/**
\brief Add a byte to the outgoing HDLC frame being built.
*/
port_INLINE void outputHdlcWrite(uint8_t b) {

}
/**
\brief Finalize the outgoing HDLC frame.
*/
port_INLINE void outputHdlcClose() {

}

//===== hdlc (input)

/**
\brief Start an HDLC frame in the input buffer.
*/
port_INLINE void inputHdlcOpen() {

}
/**
\brief Add a byte to the incoming HDLC frame.
*/
port_INLINE void inputHdlcWrite(uint8_t b) {

}
/**
\brief Finalize the incoming HDLC frame.
*/
port_INLINE void inputHdlcClose() {

}