#include "static_schedule.h"




//This address is used for node, Modify this for very different mote
uint8_t my_address = 2;

//Hardcoding of schedule for LN begins
static_schedule_entries_t static_schedule_ln[2] = {
    {  .address = {0x14,0x15,0x92,0xcc,0x00,0x00,0x00,0x01},
       .slotOffset = 3,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0xcc,0x00,0x00,0x00,0x01},
       .slotOffset = 2,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for LN ends

//Hardcoding of schedule for DAGroot begins
static_schedule_entries_t static_schedule_dr[2] = {
    {  .address = {0x14,0x15,0x92,0xcc,0x00,0x00,0x00,0x02},
       .slotOffset = 2,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0xcc,0x00,0x00,0x00,0x02},
       .slotOffset = 3,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for DAGroot ends