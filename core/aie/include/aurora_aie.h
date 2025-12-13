/*
 * Aurora Intent Engine (AIE) - Main Header
 * Core definitions and structures for AIE system
 */

#ifndef _AURORA_AIE_H
#define _AURORA_AIE_H

#include <linux/types.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/mutex.h>
#include <linux/list.h>
#include <linux/uidgid.h>
#include <linux/ktime.h>

/* AIE Version Information */
#define AIE_VERSION_MAJOR 1
#define AIE_VERSION_MINOR 0
#define AIE_VERSION_PATCH 0
#define AIE_VERSION_STRING "1.0.0"

/* AIE Device Constants */
#define AIE_MAX_CLIENTS 256
#define AIE_MAX_INTENTS 1024
#define AIE_MAX_AUTOMATIONS 512
#define AIE_MAX_RESPONSE_SIZE 4096
#define AIE_MAX_INTENT_SIZE 1024

/* AIE Intent Types */
enum aie_intent_type {
    AIE_INTENT_SYSTEM = 0,
    AIE_INTENT_SECURITY,
    AIE_INTENT_NETWORK,
    AIE_INTENT_STORAGE,
    AIE_INTENT_APPLICATION,
    AIE_INTENT_USER,
    AIE_INTENT_AUTOMATION,
    AIE_INTENT_MAX
};

/* AIE Intent Priority */
enum aie_intent_priority {
    AIE_PRIORITY_LOW = 0,
    AIE_PRIORITY_NORMAL,
    AIE_PRIORITY_HIGH,
    AIE_PRIORITY_CRITICAL,
    AIE_PRIORITY_EMERGENCY
};

/* AIE Intent Status */
enum aie_intent_status {
    AIE_STATUS_PENDING = 0,
    AIE_STATUS_PROCESSING,
    AIE_STATUS_COMPLETED,
    AIE_STATUS_FAILED,
    AIE_STATUS_CANCELLED
};

/* AIE Automation Action Types */
enum aie_action_type {
    AIE_ACTION_NONE = 0,
    AIE_ACTION_EXECUTE,
    AIE_ACTION_BLOCK,
    AIE_ACTION_LOG,
    AIE_ACTION_ALERT,
    AIE_ACTION_MODIFY,
    AIE_ACTION_REDIRECT,
    AIE_ACTION_QUARANTINE
};

/* AIE Security Levels */
enum aie_security_level {
    AIE_SECURITY_PUBLIC = 0,
    AIE_SECURITY_INTERNAL,
    AIE_SECURITY_CONFIDENTIAL,
    AIE_SECURITY_SECRET,
    AIE_SECURITY_TOP_SECRET
};

/* AIE Intent Structure */
struct aie_intent {
    u64 id;
    u32 pid;
    kuid_t uid;
    enum aie_intent_type type;
    enum aie_intent_priority priority;
    enum aie_intent_status status;
    enum aie_security_level security_level;
    ktime_t created_time;
    ktime_t processed_time;
    ktime_t completed_time;
    
    char intent_data[AIE_MAX_INTENT_SIZE];
    size_t intent_len;
    
    char response_data[AIE_MAX_RESPONSE_SIZE];
    size_t response_len;
    
    struct list_head list;
    struct mutex lock;
    
    /* Metadata */
    u32 parent_id;
    u64 correlation_id;
    bool requires_automation;
    bool security_critical;
};

/* AIE Client Structure */
struct aie_client {
    u32 pid;
    uid_t uid;
    struct mutex lock;
    struct list_head intents;
    struct list_head list;
    
    /* Statistics */
    u64 intents_submitted;
    u64 intents_completed;
    ktime_t last_activity;
};

/* AIE Automation Rule */
struct aie_automation_rule {
    u64 id;
    char name[64];
    enum aie_intent_type trigger_type;
    char trigger_pattern[256];
    enum aie_action_type action_type;
    char action_data[512];
    
    bool enabled;
    u32 priority;
    u32 timeout_ms;
    
    struct list_head list;
    struct mutex lock;
};

/* AIE Security Event */
struct aie_security_event {
    u64 id;
    u64 timestamp;
    u32 pid;
    kuid_t uid;
    enum aie_intent_type intent_type;
    enum aie_security_level security_level;
    
    char description[512];
    char details[1024];
    bool blocked;
    bool quarantined;
    
    struct list_head list;
};

/* AIE Statistics */
struct aie_stats {
    u64 intents_processed;
    u64 automations_executed;
    u64 security_events_blocked;
    u64 avg_response_ns;
    u64 success_rate;
    u64 error_count;
    u64 total_intents;
    u64 total_automations;
    u64 total_security_events;
};

/* IOCTL Commands */
#define AIE_MAGIC 'A'
#define AIE_GET_STATS _IOR(AIE_MAGIC, 1, struct aie_stats)
#define AIE_SET_MODE _IOW(AIE_MAGIC, 2, unsigned long)
#define AIE_RESET_STATS _IO(AIE_MAGIC, 3)
#define AIE_SUBMIT_INTENT _IOW(AIE_MAGIC, 4, struct aie_intent)
#define AIE_GET_INTENT _IOR(AIE_MAGIC, 5, struct aie_intent)
#define AIE_CANCEL_INTENT _IOW(AIE_MAGIC, 6, u64)
#define AIE_ADD_AUTOMATION _IOW(AIE_MAGIC, 7, struct aie_automation_rule)
#define AIE_REMOVE_AUTOMATION _IOW(AIE_MAGIC, 8, u64)
#define AIE_GET_SECURITY_EVENT _IOR(AIE_MAGIC, 9, struct aie_security_event)

/* AIE Mode Flags */
#define AIE_MODE_STANDARD 0x1
#define AIE_MODE_ENTERPRISE 0x2
#define AIE_MODE_FIPS 0x4
#define AIE_MODE_DEBUG 0x8
#define AIE_MODE_AUTONOMOUS 0x10
#define AIE_MODE_TIME_TRAVEL 0x20

/* Function Prototypes */
int aie_init_ebpf(void);
void aie_cleanup_ebpf(void);
int aie_init_intent_system(void);
void aie_cleanup_intent_system(void);
int aie_init_automation(void);
void aie_cleanup_automation(void);
int aie_init_security(void);
void aie_cleanup_security(void);

int aie_process_intent(struct aie_client *client, const char *data, size_t len);
int aie_get_client_results(struct aie_client *client, char *buffer, size_t size);
void aie_cleanup_client_intents(struct aie_client *client);
void aie_process_pending_intents(void);
void aie_execute_automations(void);
int aie_set_mode(unsigned long mode);

/* Security Functions */
int aie_check_security_policy(struct aie_intent *intent);
int aie_log_security_event(struct aie_security_event *event);
int aie_block_intent(struct aie_intent *intent);
int aie_quarantine_intent(struct aie_intent *intent);

/* Utility Functions */
u64 aie_generate_intent_id(void);
u64 aie_generate_correlation_id(void);
ktime_t aie_get_current_time(void);
const char *aie_intent_type_to_string(enum aie_intent_type type);
const char *aie_priority_to_string(enum aie_intent_priority priority);
const char *aie_status_to_string(enum aie_intent_status status);

#endif /* _AURORA_AIE_H */