
#ifndef __STATIC_SCHEDULE_H
#define __STATIC_SCHEDULE_H

#include "schedule.h"


typedef struct static_schedule_entries
{
    uint8_t address[8];
    uint8_t slotOffset;
    cellType_t link_type;
    uint8_t channelOffset;
} static_schedule_entries_t;

extern uint8_t my_address;
extern uint8_t my_channel;
extern static_schedule_entries_t static_schedule_dr[2];
extern static_schedule_entries_t static_schedule_ln1[2];
extern static_schedule_entries_t static_schedule_ln2[2];

#endif