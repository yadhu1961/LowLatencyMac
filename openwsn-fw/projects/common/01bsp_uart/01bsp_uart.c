/**
\brief This is a program which shows how to use the bsp modules for the board
       and UART.

\note: Since the bsp modules for different platforms have the same declaration,
       you can use this project with any platform.

Load this program on your board. Open a serial terminal client (e.g. PuTTY or
TeraTerm):
- You will read "Hello World!" printed over and over on your terminal client.
- when you enter a character on the client, the board echoes it back (i.e. you
  see the character on the terminal client) and the "ERROR" led blinks.

\author Thomas Watteyne <watteyne@eecs.berkeley.edu>, February 2012
*/

#include "stdint.h"
#include "stdio.h"
#include "string.h"
// bsp modules required
#include "board.h"
#include "uart.h"
#include "sctimer.h"
#include "leds.h"

//=========================== defines =========================================

#define SCTIMER_PERIOD     0x7fff // 0x7fff@32kHz = 1s

//=========================== prototypes ======================================
void cb_uartTxDone(void);
void cb_uartRxCb(void);
uint16_t counter=0;
uint16_t ticks = 0;

uint8_t test[] = {0xff,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0xee};
//=========================== main ============================================

/**
\brief The program starts executing here.
*/
int mote_main(void) {

   // initialize the board
   board_init();

   // setup UART
   uart_setCallbacks(cb_uartTxDone,cb_uartRxCb);
   uart_enableInterrupts();
   //uart_writeByte(test[0]);
   //counter++;
   while(1);
}

//=========================== callbacks =======================================
void cb_uartTxDone(void) {
  // if(counter == 1)
  // {
  //   ticks = sctimer_readCounter();
     // leds_error_toggle();
  // }
  // else if(counter < 62)
  // {
  //     uart_writeByte(test[counter]);
  //     counter++;
  // } else if(counter == 62)
  // {
  //     ticks = sctimer_readCounter()-ticks;
  //     uart_writeByte(ticks & 0xff);
  //     counter++;
  // }else
  //     return;
}

void cb_uartRxCb(void) {
   uint8_t byte;
   // toggle LED
   leds_error_toggle();
   // read received byte
   byte = uart_readByte();

  //uart_writeByte(byte);
  if(byte == 0xee)
  {
       uart_writeByte(byte);
  }
}