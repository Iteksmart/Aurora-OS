/*
 * Aurora OS AI Scheduler Header File
 * Defines interfaces and structures for AI-enhanced scheduling
 */

#ifndef _AURORA_AI_SCHEDULER_H
#define _AURORA_AI_SCHEDULER_H

#include <linux/types.h>
#include <linux/sched.h>

/* AI Scheduler Statistics Structure */
struct ai_scheduler_stats {
    u64 total_tasks;
    u64 context_switches;
    u64 prediction_accuracy;
    bool enabled;
};

/* AI Scheduler Control Functions */
void aurora_ai_scheduler_enable(bool enable);
void aurora_ai_scheduler_stats(struct ai_scheduler_stats *stats);

/* AI Scheduler Constants */
#define AI_SCHEDULER_MAX_PRIORITY 140
#define AI_SCHEDULER_MIN_PRIORITY 1
#define AI_SCHEDULER_DEFAULT_WEIGHT 1024

#endif /* _AURORA_AI_SCHEDULER_H */