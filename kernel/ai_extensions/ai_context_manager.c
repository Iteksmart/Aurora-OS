/*
 * Aurora OS - AI Context Manager Kernel Module Implementation
 * 
 * This file implements the AI-enhanced context management system for Aurora OS,
 * providing intelligent process tracking, prediction, and optimization.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/sched.h>
#include <linux/mm.h>
#include <linux/list.h>
#include <linux/spinlock.h>
#include <linux/slab.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/timer.h>
#include <linux/workqueue.h>
#include <linux/jiffies.h>
#include <linux/random.h>
#include <linux/vmalloc.h>
#include "ai_context_manager.h"

/* Module Information */
MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Aurora OS Development Team");
MODULE_DESCRIPTION("AI Context Manager for Aurora OS");
MODULE_VERSION("1.0.0");

/* Global Context Manager Instance */
struct ai_context_manager *ai_ctx_mgr = NULL;

/* Module Parameters */
unsigned int ai_context_max_processes = AI_CONTEXT_MAX_PROCESSES;
module_param(ai_context_max_processes, uint, 0644);
MODULE_PARM_DESC(ai_context_max_processes, "Maximum number of processes to track");

unsigned int ai_context_learning_interval = AI_CONTEXT_LEARNING_RATE;
module_param(ai_context_learning_interval, uint, 0644);
MODULE_PARM_DESC(ai_context_learning_interval, "Learning update interval in milliseconds");

unsigned int ai_context_prediction_threshold = AI_CONTEXT_PREDICTION_THRESHOLD;
module_param(ai_context_prediction_threshold, uint, 0644);
MODULE_PARM_DESC(ai_context_prediction_threshold, "Prediction confidence threshold (percentage)");

bool ai_context_debug_enabled = false;
module_param(ai_context_debug_enabled, bool, 0644);
MODULE_PARM_DESC(ai_context_debug_enabled, "Enable debug logging");

/* Helper Functions */
static inline ktime_t ai_context_get_current_time(void)
{
    return ktime_get();
}

static struct ai_process_context *ai_context_create_process_context(struct task_struct *task)
{
    struct ai_process_context *ctx;
    
    ctx = kzalloc(sizeof(*ctx), GFP_ATOMIC);
    if (!ctx)
        return NULL;
    
    /* Initialize basic process information */
    ctx->pid = task->pid;
    strncpy(ctx->comm, task->comm, TASK_COMM_LEN - 1);
    ctx->comm[TASK_COMM_LEN - 1] = '\0';
    
    /* Initialize tracking data */
    ctx->memory_regions = kzalloc(sizeof(unsigned long) * 16, GFP_ATOMIC);
    if (!ctx->memory_regions) {
        kfree(ctx);
        return NULL;
    }
    ctx->region_count = 0;
    
    /* Initialize timing data */
    ctx->last_cpu_update = ai_context_get_current_time();
    ctx->avg_context_switch_time = ktime_set(0, 0);
    
    /* Initialize ML scores */
    ctx->context_complexity_score = 0.5f;  /* Start with neutral complexity */
    ctx->predictability_score = 0.5f;     /* Start with neutral predictability */
    ctx->prediction_accuracy = 0;
    
    /* Initialize security context */
    ctx->security_flags = AI_CONTEXT_SECURITY_NONE;
    ctx->anomaly_count = 0;
    
    /* Initialize list and lock */
    INIT_LIST_HEAD(&ctx->list);
    spin_lock_init(&ctx->lock);
    ctx->active = true;
    
    if (ai_context_debug_enabled)
        pr_info("AI Context: Created context for process %d (%s)\n", ctx->pid, ctx->comm);
    
    return ctx;
}

/* Core Context Management Functions */
int ai_context_track_process(struct task_struct *task)
{
    struct ai_process_context *ctx;
    unsigned long flags;
    
    if (!ai_ctx_mgr || !task)
        return -EINVAL;
    
    /* Check if we're already tracking this process */
    ctx = ai_context_get_process(task->pid);
    if (ctx) {
        ctx->active = true;
        return 0;
    }
    
    /* Check process limit */
    if (ai_ctx_mgr->total_processes_tracked >= ai_context_max_processes) {
        if (ai_context_debug_enabled)
            pr_warn("AI Context: Process limit reached, not tracking PID %d\n", task->pid);
        return -ENOSPC;
    }
    
    /* Create new process context */
    ctx = ai_context_create_process_context(task);
    if (!ctx)
        return -ENOMEM;
    
    /* Add to tracked processes list */
    spin_lock_irqsave(&ai_ctx_mgr->contexts_lock, flags);
    list_add_tail(&ctx->list, &ai_ctx_mgr->process_contexts);
    ai_ctx_mgr->total_processes_tracked++;
    ai_ctx_mgr->active_processes++;
    spin_unlock_irqrestore(&ai_ctx_mgr->contexts_lock, flags);
    
    return 0;
}

int ai_context_untrack_process(pid_t pid)
{
    struct ai_process_context *ctx, *tmp;
    unsigned long flags;
    int found = 0;
    
    if (!ai_ctx_mgr)
        return -EINVAL;
    
    spin_lock_irqsave(&ai_ctx_mgr->contexts_lock, flags);
    list_for_each_entry_safe(ctx, tmp, &ai_ctx_mgr->process_contexts, list) {
        if (ctx->pid == pid) {
            ctx->active = false;
            ai_ctx_mgr->active_processes--;
            found = 1;
            break;
        }
    }
    spin_unlock_irqrestore(&ai_ctx_mgr->contexts_lock, flags);
    
    if (found && ai_context_debug_enabled)
        pr_info("AI Context: Untracking process %d\n", pid);
    
    return found ? 0 : -ENOENT;
}

struct ai_process_context *ai_context_get_process(pid_t pid)
{
    struct ai_process_context *ctx, *found = NULL;
    unsigned long flags;
    
    if (!ai_ctx_mgr)
        return NULL;
    
    spin_lock_irqsave(&ai_ctx_mgr->contexts_lock, flags);
    list_for_each_entry(ctx, &ai_ctx_mgr->process_contexts, list) {
        if (ctx->pid == pid && ctx->active) {
            found = ctx;
            break;
        }
    }
    spin_unlock_irqrestore(&ai_ctx_mgr->contexts_lock, flags);
    
    return found;
}

/* Context Analysis Functions */
void ai_context_update_cpu_usage(struct ai_process_context *ctx, struct task_struct *task)
{
    ktime_t current_time;
    u64 time_delta;
    unsigned long flags;
    
    if (!ctx || !task)
        return;
    
    spin_lock_irqsave(&ctx->lock, flags);
    
    current_time = ai_context_get_current_time();
    time_delta = ktime_to_ms(ktime_sub(current_time, ctx->last_cpu_update));
    
    if (time_delta > 0) {
        /* Update CPU time statistics */
        ctx->cpu_time_total = task->utime + task->stime;
        ctx->cpu_time_recent = task->utime + task->stime;
        
        /* Calculate CPU utilization as percentage */
        ctx->cpu_utilization = (unsigned int)((ctx->cpu_time_recent * 100) / time_delta);
        ctx->cpu_utilization = min(ctx->cpu_utilization, 100U);
        
        ctx->last_cpu_update = current_time;
    }
    
    spin_unlock_irqrestore(&ctx->lock, flags);
}

void ai_context_update_memory_usage(struct ai_process_context *ctx, struct task_struct *task)
{
    struct mm_struct *mm;
    unsigned long flags;
    
    if (!ctx || !task || !task->mm)
        return;
    
    spin_lock_irqsave(&ctx->lock, flags);
    
    mm = task->mm;
    ctx->memory_access_count++;
    
    /* Track memory regions (simplified - real implementation would track more regions) */
    if (ctx->region_count < 16) {
        /* Track some memory regions for pattern analysis */
        if (mm->start_code && mm->end_code) {
            ctx->memory_regions[ctx->region_count++] = mm->start_code;
        }
    }
    
    spin_unlock_irqrestore(&ctx->lock, flags);
}

void ai_context_analyze_patterns(struct ai_process_context *ctx)
{
    unsigned long flags;
    
    if (!ctx)
        return;
    
    spin_lock_irqsave(&ctx->lock, flags);
    
    /* Calculate context complexity score */
    /* Higher complexity if: many memory regions, high I/O, irregular CPU usage */
    float memory_factor = min(ctx->region_count / 16.0f, 1.0f);
    float io_factor = min((ctx->io_read_count + ctx->io_write_count) / 1000.0f, 1.0f);
    float cpu_variability = abs(ctx->cpu_utilization - 50) / 50.0f;  /* Distance from 50% */
    
    ctx->context_complexity_score = (memory_factor + io_factor + cpu_variability) / 3.0f;
    
    /* Calculate predictability score */
    /* Higher predictability if: regular patterns, low complexity */
    float regularity_factor = 1.0f - ctx->context_complexity_score;
    float stability_factor = ctx->anomaly_count > 0 ? 0.5f : 1.0f;
    
    ctx->predictability_score = (regularity_factor + stability_factor) / 2.0f;
    
    if (ai_context_debug_enabled && (ctx->predictability_score < 0.3f || ctx->context_complexity_score > 0.7f)) {
        pr_info("AI Context: PID %d - Complexity: %.2f, Predictability: %.2f\n",
                ctx->pid, ctx->context_complexity_score, ctx->predictability_score);
    }
    
    spin_unlock_irqrestore(&ctx->lock, flags);
}

/* Prediction Engine */
int ai_context_predict_next_switch(struct ai_process_context *ctx, struct ai_context_prediction *pred)
{
    ktime_t avg_switch_time;
    unsigned long flags;
    int confidence;
    
    if (!ctx || !pred)
        return -EINVAL;
    
    spin_lock_irqsave(&ctx->lock, flags);
    
    /* Simple prediction based on average context switch time */
    avg_switch_time = ctx->avg_context_switch_time;
    
    /* Add some randomness for variety */
    if (avg_switch_time.tv64 > 0) {
        u64 random_factor = get_random_u32() % 20 - 10;  /* +/- 10% variance */
        s64 adjusted_time = avg_switch_time.tv64 * (100 + random_factor) / 100;
        pred->predicted_next_switch = ktime_set(0, adjusted_time);
    } else {
        pred->predicted_next_switch = ktime_set(0, 10000000);  /* Default 10ms */
    }
    
    /* Calculate confidence based on predictability score */
    confidence = (int)(ctx->predictability_score * 100);
    pred->confidence = confidence;
    pred->is_prediction_valid = (confidence >= ai_context_prediction_threshold);
    
    pred->pid = ctx->pid;
    pred->predicted_memory_usage = 1024 * 1024;  /* Simple prediction */
    pred->predicted_cpu_usage = ctx->cpu_utilization;
    
    spin_unlock_irqrestore(&ctx->lock, flags);
    
    ai_ctx_mgr->predictions_made++;
    
    return 0;
}

/* Security Monitoring */
int ai_context_security_analyze(struct ai_process_context *ctx)
{
    unsigned long flags;
    unsigned int new_flags = AI_CONTEXT_SECURITY_NONE;
    
    if (!ctx)
        return -EINVAL;
    
    spin_lock_irqsave(&ctx->lock, flags);
    
    /* Check for suspicious patterns */
    if (ctx->context_complexity_score > 0.8f) {
        new_flags |= AI_CONTEXT_SECURITY_SUSPICIOUS;
    }
    
    if (ctx->anomaly_count > 5) {
        new_flags |= AI_CONTEXT_SECURITY_ANOMALY;
    }
    
    /* Check for unusual I/O patterns (potential malware) */
    if (ctx->io_write_count > 10000 && ctx->io_read_count < 1000) {
        new_flags |= AI_CONTEXT_SECURITY_MALWARE;
    }
    
    ctx->security_flags |= new_flags;
    
    spin_unlock_irqrestore(&ctx->lock, flags);
    
    return new_flags;
}

/* Learning System */
void ai_context_learning_work(struct work_struct *work)
{
    struct ai_process_context *ctx, *tmp;
    unsigned long flags;
    
    if (!ai_ctx_mgr)
        return;
    
    /* Clean up inactive processes */
    spin_lock_irqsave(&ai_ctx_mgr->contexts_lock, flags);
    list_for_each_entry_safe(ctx, tmp, &ai_ctx_mgr->process_contexts, list) {
        if (!ctx->active) {
            list_del(&ctx->list);
            kfree(ctx->memory_regions);
            kfree(ctx);
            ai_ctx_mgr->total_processes_tracked--;
        }
    }
    spin_unlock_irqrestore(&ai_ctx_mgr->contexts_lock, flags);
    
    /* Analyze patterns for all active processes */
    list_for_each_entry(ctx, &ai_ctx_mgr->process_contexts, list) {
        if (ctx->active) {
            ai_context_analyze_patterns(ctx);
            ai_context_security_analyze(ctx);
        }
    }
    
    ai_ctx_mgr->last_learning_update = ai_context_get_current_time();
    
    if (ai_context_debug_enabled)
        pr_info("AI Context: Learning update completed\n");
}

/* Learning Timer Callback */
static void ai_context_learning_timer_callback(struct timer_list *timer)
{
    static struct work_struct learning_work;
    
    /* Schedule learning work */
    INIT_WORK(&learning_work, ai_context_learning_work);
    schedule_work(&learning_work);
    
    /* Reschedule timer */
    mod_timer(timer, jiffies + msecs_to_jiffies(ai_context_learning_interval));
}

/* ProcFS Interface */
static int ai_context_proc_show_stats(struct seq_file *m, void *v)
{
    if (!ai_ctx_mgr) {
        seq_printf(m, "AI Context Manager not initialized\n");
        return 0;
    }
    
    seq_printf(m, "=== AI Context Manager Statistics ===\n");
    seq_printf(m, "Total Processes Tracked: %u\n", ai_ctx_mgr->total_processes_tracked);
    seq_printf(m, "Active Processes: %u\n", ai_ctx_mgr->active_processes);
    seq_printf(m, "Predictions Made: %u\n", ai_ctx_mgr->predictions_made);
    seq_printf(m, "Prediction Hits: %llu\n", ai_ctx_mgr->prediction_hits);
    seq_printf(m, "Prediction Misses: %llu\n", ai_ctx_mgr->prediction_misses);
    seq_printf(m, "Total Context Switches: %llu\n", ai_ctx_mgr->total_context_switches);
    seq_printf(m, "Learning Interval: %u ms\n", ai_context_learning_interval);
    seq_printf(m, "Prediction Threshold: %u%%\n", ai_context_prediction_threshold);
    seq_printf(m, "Debug Mode: %s\n", ai_context_debug_enabled ? "Enabled" : "Disabled");
    
    return 0;
}

static int ai_context_proc_show_contexts(struct seq_file *m, void *v)
{
    struct ai_process_context *ctx;
    
    if (!ai_ctx_mgr) {
        seq_printf(m, "AI Context Manager not initialized\n");
        return 0;
    }
    
    seq_printf(m, "=== Tracked Process Contexts ===\n");
    seq_printf(m, "PID\tName\t\tCPU%%\tComplexity\tPredictability\tSecurity\n");
    seq_printf(m, "------------------------------------------------------------\n");
    
    list_for_each_entry(ctx, &ai_ctx_mgr->process_contexts, list) {
        if (ctx->active) {
            seq_printf(m, "%d\t%-15s\t%u%%\t%.2f\t\t%.2f\t\t0x%x\n",
                      ctx->pid, ctx->comm, ctx->cpu_utilization,
                      ctx->context_complexity_score, ctx->predictability_score,
                      ctx->security_flags);
        }
    }
    
    return 0;
}

/* ProcFS Initialization */
int ai_context_proc_init(void)
{
    if (!ai_ctx_mgr)
        return -EINVAL;
    
    ai_ctx_mgr->proc_dir = proc_mkdir("ai_context", NULL);
    if (!ai_ctx_mgr->proc_dir)
        return -ENOMEM;
    
    ai_ctx_mgr->proc_stats = proc_create_single("stats", 0444, ai_ctx_mgr->proc_dir,
                                                ai_context_proc_show_stats);
    if (!ai_ctx_mgr->proc_stats)
        goto cleanup_stats;
    
    ai_ctx_mgr->proc_contexts = proc_create_single("contexts", 0444, ai_ctx_mgr->proc_dir,
                                                  ai_context_proc_show_contexts);
    if (!ai_ctx_mgr->proc_contexts)
        goto cleanup_contexts;
    
    return 0;
    
cleanup_contexts:
    remove_proc_entry("stats", ai_ctx_mgr->proc_dir);
cleanup_stats:
    remove_proc_entry("ai_context", NULL);
    return -ENOMEM;
}

void ai_context_proc_cleanup(void)
{
    if (!ai_ctx_mgr)
        return;
    
    if (ai_ctx_mgr->proc_contexts)
        remove_proc_entry("contexts", ai_ctx_mgr->proc_dir);
    if (ai_ctx_mgr->proc_stats)
        remove_proc_entry("stats", ai_ctx_mgr->proc_dir);
    if (ai_ctx_mgr->proc_dir)
        remove_proc_entry("ai_context", NULL);
}

/* Module Initialization */
int ai_context_init(void)
{
    int ret;
    
    pr_info("AI Context Manager: Initializing Aurora OS AI Context Manager\n");
    
    /* Allocate context manager structure */
    ai_ctx_mgr = kzalloc(sizeof(*ai_ctx_mgr), GFP_KERNEL);
    if (!ai_ctx_mgr) {
        pr_err("AI Context Manager: Failed to allocate context manager\n");
        return -ENOMEM;
    }
    
    /* Initialize context manager */
    INIT_LIST_HEAD(&ai_ctx_mgr->process_contexts);
    spin_lock_init(&ai_ctx_mgr->contexts_lock);
    
    ai_ctx_mgr->total_processes_tracked = 0;
    ai_ctx_mgr->active_processes = 0;
    ai_ctx_mgr->predictions_made = 0;
    ai_ctx_mgr->predictions_correct = 0;
    ai_ctx_mgr->prediction_hits = 0;
    ai_ctx_mgr->prediction_misses = 0;
    
    ai_ctx_mgr->last_learning_update = ai_context_get_current_time();
    
    /* Initialize learning timer */
    timer_setup(&ai_ctx_mgr->learning_timer, ai_context_learning_timer_callback, 0);
    mod_timer(&ai_ctx_mgr->learning_timer, 
              jiffies + msecs_to_jiffies(ai_context_learning_interval));
    
    /* Initialize ProcFS interface */
    ret = ai_context_proc_init();
    if (ret) {
        pr_err("AI Context Manager: Failed to initialize ProcFS interface\n");
        kfree(ai_ctx_mgr);
        return ret;
    }
    
    pr_info("AI Context Manager: Successfully initialized\n");
    pr_info("AI Context Manager: Max processes: %u, Learning interval: %u ms\n",
            ai_context_max_processes, ai_context_learning_interval);
    
    return 0;
}

/* Module Cleanup */
void ai_context_exit(void)
{
    struct ai_process_context *ctx, *tmp;
    unsigned long flags;
    
    if (!ai_ctx_mgr)
        return;
    
    pr_info("AI Context Manager: Shutting down\n");
    
    /* Cancel learning timer */
    del_timer_sync(&ai_ctx_mgr->learning_timer);
    
    /* Clean up all process contexts */
    spin_lock_irqsave(&ai_ctx_mgr->contexts_lock, flags);
    list_for_each_entry_safe(ctx, tmp, &ai_ctx_mgr->process_contexts, list) {
        list_del(&ctx->list);
        kfree(ctx->memory_regions);
        kfree(ctx);
    }
    spin_unlock_irqrestore(&ai_ctx_mgr->contexts_lock, flags);
    
    /* Clean up ProcFS interface */
    ai_context_proc_cleanup();
    
    /* Free context manager */
    kfree(ai_ctx_mgr);
    ai_ctx_mgr = NULL;
    
    pr_info("AI Context Manager: Shutdown complete\n");
}

/* Hook Implementations */
#ifdef CONFIG_AURORA_AI_HOOKS
void ai_context_sched_switch_hook(struct task_struct *prev, struct task_struct *next)
{
    struct ai_process_context *ctx;
    ktime_t switch_time, duration;
    
    if (!ai_ctx_mgr)
        return;
    
    /* Update statistics */
    ai_ctx_mgr->total_context_switches++;
    switch_time = ai_context_get_current_time();
    
    /* Track previous process */
    ctx = ai_context_get_process(prev->pid);
    if (ctx) {
        /* Calculate context switch duration */
        if (ctx->switch_history_index > 0) {
            duration = ktime_sub(switch_time, 
                               ctx->context_switch_times[ctx->switch_history_index - 1]);
            /* Update average context switch time */
            if (ctx->avg_context_switch_time.tv64 == 0) {
                ctx->avg_context_switch_time = duration;
            } else {
                ctx->avg_context_switch_time = ktime_add(ctx->avg_context_switch_time, duration);
                ctx->avg_context_switch_time.tv64 /= 2;  /* Simple average */
            }
        }
        
        /* Store switch time */
        ctx->context_switch_times[ctx->switch_history_index] = switch_time;
        ctx->switch_history_index = (ctx->switch_history_index + 1) % AI_CONTEXT_HISTORY_SIZE;
        
        /* Update process statistics */
        ai_context_update_cpu_usage(ctx, prev);
        ai_context_update_memory_usage(ctx, prev);
    }
    
    /* Track next process */
    ctx = ai_context_get_process(next->pid);
    if (!ctx) {
        /* Auto-track new processes */
        ai_context_track_process(next);
    }
}

void ai_context_fork_hook(struct task_struct *parent, struct task_struct *child)
{
    struct ai_process_context *parent_ctx, *child_ctx;
    
    if (!ai_ctx_mgr)
        return;
    
    /* Get parent context */
    parent_ctx = ai_context_get_process(parent->pid);
    if (!parent_ctx)
        return;
    
    /* Track child process */
    ai_context_track_process(child);
    child_ctx = ai_context_get_process(child->pid);
    if (!child_ctx)
        return;
    
    /* Inherit some characteristics from parent */
    child_ctx->context_complexity_score = parent_ctx->context_complexity_score;
    child_ctx->predictability_score = parent_ctx->predictability_score;
    
    if (ai_context_debug_enabled)
        pr_info("AI Context: Fork detected - Parent: %d, Child: %d\n", parent->pid, child->pid);
}

void ai_context_exit_hook(struct task_struct *task)
{
    if (!ai_ctx_mgr)
        return;
    
    ai_context_untrack_process(task->pid);
    
    if (ai_context_debug_enabled)
        pr_info("AI Context: Process exit detected - PID: %d\n", task->pid);
}
#endif

/* Module Registration */
module_init(ai_context_init);
module_exit(ai_context_exit);