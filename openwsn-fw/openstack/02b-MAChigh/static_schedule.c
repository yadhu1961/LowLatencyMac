#include "static_schedule.h"


#ifdef DG

uint8_t my_channel = 26;//Synchronizing channel

uint8_t beacon_slot_offset[] = {0,2};
//Hardcoding of schedule for DAGroot begins
static_schedule_entries_t static_schedule_dr[2] = {
    {  .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02},
       .slotOffset = 3,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02},
       .slotOffset = 2,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for DAGroot ends
#endif

#ifdef LN1
//Control loop1 channel
uint8_t my_channel = 22;

uint8_t beacon_slot_offset[] = {2};
//Hardcoding of schedule for LN begins
static_schedule_entries_t static_schedule_ln1[2] = {
    {  .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x03},
       .slotOffset = 1,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x03},
       .slotOffset = 4,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for LN ends
#endif


#ifdef LN2

//Control loop1 channel
uint8_t my_channel = 22;

uint8_t beacon_slot_offset[] = {0};
//Hardcoding of schedule for LN begins
static_schedule_entries_t static_schedule_ln2[2] = {
    {  .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02},
       .slotOffset = 4,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x02},
       .slotOffset = 1,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for LN ends
#endif


#ifdef LN3

//Control loop2 channel
uint8_t my_channel = 18;

uint8_t beacon_slot_offset[] = {2};
//Hardcoding of schedule for LN begins
static_schedule_entries_t static_schedule_ln1[2] = {
    {  .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x05},
       .slotOffset = 1,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x05},
       .slotOffset = 4,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for LN ends
#endif


#ifdef LN4

//Control loop2 channel
uint8_t my_channel = 18;

uint8_t beacon_slot_offset[] = {0};
//Hardcoding of schedule for LN begins
static_schedule_entries_t static_schedule_ln2[2] = {
    {  .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x04},
       .slotOffset = 4,
       .link_type = CELLTYPE_TX,
       .channelOffset = 1
    },
    {
        .address = {0x14,0x15,0x92,0x00,0x00,0x00,0x00,0x04},
       .slotOffset = 1,
       .link_type = CELLTYPE_RX,
       .channelOffset = SCHEDULE_MINIMAL_6TISCH_CHANNELOFFSET
    }
};
//Hardcoding of schedule for LN ends
#endif