/**
\brief Declaration of the "openserial" driver.

\author Fabien Chraim <chraim@eecs.berkeley.edu>, March 2012.
\author Thomas Watteyne <thomas.watteyne@inria.fr>, August 2016.
*/

#ifndef __OPENSERIAL_H
#define __OPENSERIAL_H

#include "opendefs.h"
#include "openudp.h"


/**
 * @brief      { Macro for allocating the circular buffer }
 *
 * @param      x     { name of the  buffer which needs to be created}
 * @param      y     { Size of the buffer }
 *
 * @return     { Creates  a circular buffer of the given name and size}
 */
#define CIRCBUF_DEF(x,y)          \
    uint8_t x##_space[y];     \
    circBuf_t x = {               \
        .buffer = x##_space,      \
        .head = 0,                \
        .tail = 0,                \
        .maxLen = y               \
    }

/**
\addtogroup drivers
\{
\addtogroup OpenSerial
\{
*/

//=========================== define ==========================================

/**
\brief Number of bytes of the serial output buffer, in bytes.

\warning should be exactly 256 so wrap-around on the index does not require
         the use of a slow modulo operator.
*/
#define SERIAL_OUTPUT_BUFFER_SIZE 256 // leave at 256! tx buffer of uart

/**
\brief Number of bytes of the serial input buffer, in bytes.

\warning Do not pick a number greater than 255, since its filling level is
         encoded by a single byte in the code.
*/
#define SERIAL_INPUT_BUFFER_SIZE  256 //is nothing bu rx buffer of uart

/**
 * {serial port commands which are related to data processing must
 * be prefixed by 'D'}
 */
#define DATA_COMMAND ((uint8_t)'D')

/**
 * {serial port commands which are related to control must
 * be prefixed by 'E'}
 */
#define CONTROL_COMMAND ((uint8_t)'C')

#define REQUEST_FRAME ((uint8_t)'S')


#define SERIAL_MSG_PKT 'P'

#define SERIAL_MSG_ERR 'E'

#define SERIAL_MSG_DEB 'D'

#define SERIAL_MSG_RSP 'R'


#define START_FLAG            0x7E

/// Modes of the openserial module.
enum
{
   MODE_OFF,    //< The module is off, no serial activity.
   MODE_INPUT,  //< The serial is listening or receiving bytes.
   MODE_OUTPUT  //< The serial is transmitting bytes.
};

//=========================== variables =======================================

//=========================== prototypes ======================================

typedef void (*openserial_cbt)(void);

//Used by userserial bridge so left as dummy, Not used in openserial module
typedef struct _openserial_rsvpt {
    uint8_t                       cmdId; ///< serial command (e.g. 'B')
    openserial_cbt                cb;    ///< handler of that command
    struct _openserial_rsvpt*     next;  ///< pointer to the next registered command
} openserial_rsvpt;

typedef struct {
    // admin
    uint8_t             mode;
    // input
    uint8_t             reqFrame[1+1+1];
    uint8_t             reqFrameIdx;
    bool busy_tx;
    uint8_t bytes_transmitted,tx_pkt_len;
    uint16_t total_bytes_transmitted;
} openserial_vars_t;

/**
 * { structure for ring buffer implementation}
 */
typedef struct {
    uint8_t * const buffer;
    int head;
    int tail;
    uint8_t fill_level;
    const int maxLen;
} circBuf_t;

//Needed for injecting udp packets from serial port
typedef struct {
   udp_resource_desc_t     desc;  ///< resource descriptor for this module, used to register at UDP stack
} udp_inject_vars_t;

// admin
void      openserial_init(void);
void      openserial_register(openserial_rsvpt* rsvp);

// printing
owerror_t openserial_printStatus(
    uint8_t             statusElement,
    uint8_t*            buffer,
    uint8_t             length
);
owerror_t openserial_printInfo(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
);
owerror_t openserial_printError(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
);
owerror_t openserial_printCritical(
    uint8_t             calling_component,
    uint8_t             error_code,
    errorparameter_t    arg1,
    errorparameter_t    arg2
);
owerror_t openserial_printData(uint8_t* buffer, uint8_t length);
owerror_t openserial_printSniffedPacket(uint8_t* buffer, uint8_t length, uint8_t channel);

// retrieving inputBuffer
uint8_t   openserial_getInputBufferFilllevel(void);
uint8_t   openserial_getInputBuffer(uint8_t* bufferToWrite, uint8_t maxNumBytes);

// scheduling
void      openserial_startInput(uint8_t asn,uint16_t schedule_offset);
void      openserial_startOutput(uint8_t,uint16_t);
void      openserial_stop(void);

// debugprint
bool      debugPrint_outBufferIndexes(void);

// interrupt handlers
void      isr_openserial_rx(void);
void      isr_openserial_tx(void);

/**
 * @brief      { function used for printing serial debugging messages}
 *
 * @param      ch        {  pointer to string array }
 * @param[in]  data_len   { The data length }
 *
 * @return     { returns the  number of bytes which are added to buffer}
 */
uint8_t openserial_printf(char *ch,uint8_t data_len,uint8_t type);

/**
\}
\}
*/

#endif