/*
 * Aurora OS - AI Context Manager Kernel Module
 * 
 * This module provides AI-enhanced context management for the Linux kernel,
 * enabling intelligent process context tracking and optimization.
 * 
 * Key Features:
 * - Process context learning and prediction
 * - Memory access pattern analysis
 * - Context-aware resource allocation
 * - Intelligent context switching
 * - Security context monitoring
 */

#ifndef AI_CONTEXT_MANAGER_H
#define AI_CONTEXT_MANAGER_H

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/mm.h>
#include <linux/list.h>
#include <linux/spinlock.h>
#include <linux/ktime.h>
#include <linux/proc_fs.h>

/* Context Manager Configuration */
#define AI_CONTEXT_MAX_PROCESSES    1024
#define AI_CONTEXT_HISTORY_SIZE     64
#define AI_CONTEXT_LEARNING_RATE    1000  /* milliseconds */
#define AI_CONTEXT_PREDICTION_THRESHOLD  75  /* percentage */

/* Process Context Data Structure */
struct ai_process_context {
    pid_t pid;                          /* Process ID */
    char comm[TASK_COMM_LEN];           /* Process name */
    
    /* Memory Access Patterns */
    unsigned long memory_access_count;
    unsigned long *memory_regions;      /* Tracked memory regions */
    unsigned int region_count;
    
    /* CPU Usage Patterns */
    u64 cpu_time_total;
    u64 cpu_time_recent;
    ktime_t last_cpu_update;
    unsigned int cpu_utilization;
    
    /* I/O Patterns */
    unsigned long io_read_count;
    unsigned long io_write_count;
    u64 io_bytes_read;
    u64 io_bytes_written;
    
    /* Context Switch History */
    ktime_t context_switch_times[AI_CONTEXT_HISTORY_SIZE];
    unsigned int switch_history_index;
    ktime_t avg_context_switch_time;
    
    /* ML Features */
    float context_complexity_score;     /* 0.0 - 1.0 */
    float predictability_score;         /* 0.0 - 1.0 */
    unsigned int prediction_accuracy;
    
    /* Security Context */
    unsigned int security_flags;        /* Security-related behaviors */
    unsigned int anomaly_count;
    
    /* List Management */
    struct list_head list;
    spinlock_t lock;
    bool active;
};

/* Context Prediction Data */
struct ai_context_prediction {
    pid_t pid;
    ktime_t predicted_next_switch;
    unsigned long predicted_memory_usage;
    unsigned int predicted_cpu_usage;
    float confidence;
    bool is_prediction_valid;
};

/* Context Manager State */
struct ai_context_manager {
    struct list_head process_contexts;  /* List of tracked processes */
    spinlock_t contexts_lock;           /* Protect process contexts */
    
    /* Statistics */
    unsigned int total_processes_tracked;
    unsigned int active_processes;
    unsigned int predictions_made;
    unsigned int predictions_correct;
    
    /* Learning State */
    ktime_t last_learning_update;
    struct timer_list learning_timer;
    
    /* ProcFS Interface */
    struct proc_dir_entry *proc_dir;
    struct proc_dir_entry *proc_stats;
    struct proc_dir_entry *proc_contexts;
    
    /* Performance Metrics */
    u64 total_context_switches;
    ktime_t total_context_switch_time;
    u64 prediction_hits;
    u64 prediction_misses;
};

/* Security Context Flags */
#define AI_CONTEXT_SECURITY_NONE        0x0000
#define AI_CONTEXT_SECURITY_PRIV_ESCAL  0x0001  /* Privilege escalation */
#define AI_CONTEXT_SECURITY_SUSPICIOUS  0x0002  /* Suspicious behavior */
#define AI_CONTEXT_SECURITY_ANOMALY     0x0004  /* Anomaly detected */
#define AI_CONTEXT_SECURITY_MALWARE     0x0008  /* Potential malware */

/* Function Prototypes */

/* Core Context Management */
int ai_context_init(void);
void ai_context_exit(void);
int ai_context_track_process(struct task_struct *task);
int ai_context_untrack_process(pid_t pid);
struct ai_process_context *ai_context_get_process(pid_t pid);

/* Context Analysis */
void ai_context_update_cpu_usage(struct ai_process_context *ctx, struct task_struct *task);
void ai_context_update_memory_usage(struct ai_process_context *ctx, struct task_struct *task);
void ai_context_update_io_stats(struct ai_process_context *ctx, struct task_struct *task);
void ai_context_analyze_patterns(struct ai_process_context *ctx);

/* Prediction Engine */
int ai_context_predict_next_switch(struct ai_process_context *ctx, struct ai_context_prediction *pred);
int ai_context_predict_resource_usage(struct ai_process_context *ctx, unsigned long *memory, unsigned int *cpu);
void ai_context_update_prediction_accuracy(struct ai_context_prediction *pred, bool was_correct);

/* Security Monitoring */
int ai_context_security_analyze(struct ai_process_context *ctx);
void ai_context_detect_anomalies(struct ai_process_context *ctx);
bool ai_context_is_suspicious(struct ai_process_context *ctx);

/* Learning System */
void ai_context_learning_work(struct work_struct *work);
void ai_context_update_model(void);
void ai_context_cleanup_old_data(void);

/* ProcFS Interface */
int ai_context_proc_init(void);
void ai_context_proc_cleanup(void);
int ai_context_proc_read_stats(char *buffer, char **start, off_t offset, int count, int *eof, void *data);
int ai_context_proc_read_contexts(char *buffer, char **start, off_t offset, int count, int *eof, void *data);

/* Utility Functions */
ktime_t ai_context_get_current_time(void);
float ai_context_calculate_complexity(struct ai_process_context *ctx);
float ai_context_calculate_predictability(struct ai_process_context *ctx);
void ai_context_dump_process_info(struct ai_process_context *ctx);

/* Hooks Integration */
#ifdef CONFIG_AURORA_AI_HOOKS
void ai_context_sched_switch_hook(struct task_struct *prev, struct task_struct *next);
void ai_context_fork_hook(struct task_struct *parent, struct task_struct *child);
void ai_context_exit_hook(struct task_struct *task);
#endif

/* Global Variables */
extern struct ai_context_manager *ai_ctx_mgr;

/* Module Parameters */
extern unsigned int ai_context_max_processes;
extern unsigned int ai_context_learning_interval;
extern unsigned int ai_context_prediction_threshold;
extern bool ai_context_debug_enabled;

#endif /* AI_CONTEXT_MANAGER_H */