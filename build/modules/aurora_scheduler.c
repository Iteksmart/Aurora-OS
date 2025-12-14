/*
 * Aurora OS AI-Aware Process Scheduler
 * Optimizes scheduling for AI workloads with real-time performance guarantees
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/sched.h>
#include <linux/sched/rt.h>
#include <linux/sched/signal.h>
#include <linux/cpumask.h>
#include <linux/cpu.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <linux/percpu.h>
#include <linux/spinlock.h>
#include <linux/slab.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>

// AI task priorities
#define AURORA_AI_PRIORITY_LOW      100
#define AURORA_AI_PRIORITY_NORMAL   50
#define AURORA_AI_PRIORITY_HIGH     10
#define AURORA_AI_PRIORITY_CRITICAL 1

// AI task types
#define AURORA_TASK_INFERENCE    1
#define AURORA_TASK_TRAINING     2
#define AURORA_TASK_PREPROCESS   3
#define AURORA_TASK_POSTPROCESS  4
#define AURORA_TASK_OPTIMIZATION 5

// Per-CPU scheduler data
struct aurora_cpu_data {
    spinlock_t lock;
    struct list_head ai_tasks;
    unsigned long ai_load;
    unsigned int ai_task_count;
    struct timer_list balance_timer;
    unsigned long last_balance;
};

// AI task descriptor
struct aurora_ai_task {
    struct list_head list;
    struct task_struct *task;
    int ai_type;
    int ai_priority;
    unsigned long estimated_runtime;
    unsigned long deadline;
    int preferred_cpu;
    bool real_time;
    struct completion completion;
};

// Global scheduler state
static struct aurora_cpu_data __percpu *cpu_data;
static struct proc_dir_entry *aurora_proc_dir;
static struct proc_dir_entry *aurora_scheduler_proc;

// CPU hotplug notifications
static int aurora_cpu_callback(struct notifier_block *nfb, 
                               unsigned long action, void *hcpu);
static struct notifier_block aurora_cpu_notifier = {
    .notifier_call = aurora_cpu_callback,
};

// Statistics
static atomic_t total_ai_tasks = ATOMIC_INIT(0);
static atomic_t completed_ai_tasks = ATOMIC_INIT(0);
static atomic_t missed_deadlines = ATOMIC_INIT(0);

// Initialize AI scheduler for a CPU
static int aurora_init_cpu(int cpu)
{
    struct aurora_cpu_data *data = per_cpu_ptr(cpu_data, cpu);
    
    spin_lock_init(&data->lock);
    INIT_LIST_HEAD(&data->ai_tasks);
    data->ai_load = 0;
    data->ai_task_count = 0;
    data->last_balance = jiffies;
    
    // Setup load balancing timer
    timer_setup(&data->balance_timer, aurora_balance_timer_fn, 0);
    mod_timer(&data->balance_timer, jiffies + HZ);
    
    pr_info("Aurora AI scheduler initialized for CPU %d\n", cpu);
    return 0;
}

// AI task classification
static int classify_ai_task(struct task_struct *task)
{
    // Check task name and properties to classify AI workloads
    if (strstr(task->comm, "inference") || strstr(task->comm, "tensorflow"))
        return AURORA_TASK_INFERENCE;
    if (strstr(task->comm, "train") || strstr(task->comm, "pytorch"))
        return AURORA_TASK_TRAINING;
    if (strstr(task->comm, "preprocess") || strstr(task->comm, "data"))
        return AURORA_TASK_PREPROCESS;
    if (strstr(task->comm, "optimize") || strstr(task->comm, "tune"))
        return AURORA_TASK_OPTIMIZATION;
    
    return AURORA_TASK_POSTPROCESS; // Default
}

// Determine AI task priority
static int get_ai_priority(struct task_struct *task, int ai_type)
{
    int base_priority;
    
    switch (ai_type) {
    case AURORA_TASK_INFERENCE:
        base_priority = AURORA_AI_PRIORITY_HIGH;
        break;
    case AURORA_TASK_TRAINING:
        base_priority = AURORA_AI_PRIORITY_NORMAL;
        break;
    case AURORA_TASK_OPTIMIZATION:
        base_priority = AURORA_AI_PRIORITY_LOW;
        break;
    default:
        base_priority = AURORA_AI_PRIORITY_NORMAL;
    }
    
    // Adjust based on task properties
    if (task->prio < MAX_RT_PRIO)  // Real-time task
        base_priority = AURORA_AI_PRIORITY_CRITICAL;
    
    // Consider nice value
    if (task_nice(task) < 0)
        base_priority = max(base_priority - 10, 1);
    
    return base_priority;
}

// Estimate task runtime based on AI type and history
static unsigned long estimate_runtime(struct task_struct *task, int ai_type)
{
    static unsigned long avg_runtimes[] = {
        [AURORA_TASK_INFERENCE]    = 100,  // ms
        [AURORA_TASK_TRAINING]     = 5000, // ms
        [AURORA_TASK_PREPROCESS]   = 50,   // ms
        [AURORA_TASK_POSTPROCESS]  = 30,   // ms
        [AURORA_TASK_OPTIMIZATION] = 2000, // ms
    };
    
    if (ai_type >= ARRAY_SIZE(avg_runtimes))
        return 1000; // Default 1 second
    
    return avg_runtimes[ai_type];
}

// Add AI task to scheduler
static void add_ai_task(struct task_struct *task)
{
    struct aurora_ai_task *ai_task;
    struct aurora_cpu_data *data;
    int cpu = task_cpu(task);
    int ai_type;
    
    ai_task = kzalloc(sizeof(*ai_task), GFP_ATOMIC);
    if (!ai_task)
        return;
    
    ai_type = classify_ai_task(task);
    ai_task->task = task;
    ai_task->ai_type = ai_type;
    ai_task->ai_priority = get_ai_priority(task, ai_type);
    ai_task->estimated_runtime = estimate_runtime(task, ai_type);
    ai_task->deadline = jiffies + msecs_to_jiffies(ai_task->estimated_runtime * 2);
    ai_task->real_time = (task->prio < MAX_RT_PRIO);
    init_completion(&ai_task->completion);
    
    // Select optimal CPU
    ai_task->preferred_cpu = select_optimal_cpu(task, ai_type);
    
    data = per_cpu_ptr(cpu_data, ai_task->preferred_cpu);
    spin_lock(&data->lock);
    
    // Insert into priority queue
    list_add_tail(&ai_task->list, &data->ai_tasks);
    data->ai_task_count++;
    data->ai_load += ai_task->estimated_runtime;
    
    spin_unlock(&data->lock);
    
    atomic_inc(&total_ai_tasks);
    
    // Adjust task scheduling parameters
    set_task_rt_priority(task, ai_task->ai_priority);
    
    pr_debug("Added AI task %s (type %d, priority %d) to CPU %d\n",
             task->comm, ai_type, ai_task->ai_priority, ai_task->preferred_cpu);
}

// Remove AI task from scheduler
static void remove_ai_task(struct task_struct *task)
{
    struct aurora_ai_task *ai_task, *tmp;
    struct aurora_cpu_data *data;
    int cpu = task_cpu(task);
    
    data = per_cpu_ptr(cpu_data, cpu);
    spin_lock(&data->lock);
    
    list_for_each_entry_safe(ai_task, tmp, &data->ai_tasks, list) {
        if (ai_task->task == task) {
            list_del(&ai_task->list);
            data->ai_task_count--;
            data->ai_load -= ai_task->estimated_runtime;
            kfree(ai_task);
            atomic_inc(&completed_ai_tasks);
            break;
        }
    }
    
    spin_unlock(&data->lock);
}

// Select optimal CPU for AI task
static int select_optimal_cpu(struct task_struct *task, int ai_type)
{
    int cpu, best_cpu = -1;
    unsigned long min_load = ULONG_MAX;
    struct aurora_cpu_data *data;
    
    // For real-time tasks, prefer isolated CPUs
    if (task->prio < MAX_RT_PRIO) {
        for_each_online_cpu(cpu) {
            if (cpumask_test_cpu(cpu, cpu_isolated_mask)) {
                data = per_cpu_ptr(cpu_data, cpu);
                if (data->ai_task_count < 2) { // Low load
                    return cpu;
                }
            }
        }
    }
    
    // For training tasks, prefer high-performance CPUs
    if (ai_type == AURORA_TASK_TRAINING) {
        for_each_online_cpu(cpu) {
            if (cpu_capacity(cpu) > 500) { // High capacity CPU
                data = per_cpu_ptr(cpu_data, cpu);
                if (data->ai_load < min_load) {
                    min_load = data->ai_load;
                    best_cpu = cpu;
                }
            }
        }
    }
    
    // Default: least loaded CPU
    if (best_cpu == -1) {
        for_each_online_cpu(cpu) {
            data = per_cpu_ptr(cpu_data, cpu);
            if (data->ai_load < min_load) {
                min_load = data->ai_load;
                best_cpu = cpu;
            }
        }
    }
    
    return best_cpu >= 0 ? best_cpu : smp_processor_id();
}

// Load balancing timer function
static void aurora_balance_timer_fn(struct timer_list *t)
{
    struct aurora_cpu_data *data = this_cpu_ptr(cpu_data);
    unsigned long now = jiffies;
    
    // Check for deadline misses
    struct aurora_ai_task *ai_task, *tmp;
    
    spin_lock(&data->lock);
    
    list_for_each_entry_safe(ai_task, tmp, &data->ai_tasks, list) {
        if (time_after(now, ai_task->deadline)) {
            atomic_inc(&missed_deadlines);
            pr_warn("AI task %s missed deadline on CPU %d\n",
                    ai_task->task->comm, smp_processor_id());
        }
    }
    
    // Rebalance if needed
    if (data->ai_task_count > 5 && time_after(now, data->last_balance + HZ)) {
        aurora_rebalance_tasks(data);
        data->last_balance = now;
    }
    
    spin_unlock(&data->lock);
    
    // Reschedule timer
    mod_timer(&data->balance_timer, now + HZ/4);
}

// Rebalance AI tasks between CPUs
static void aurora_rebalance_tasks(struct aurora_cpu_data *src_data)
{
    struct aurora_ai_task *ai_task, *tmp;
    struct aurora_cpu_data *dst_data;
    int dst_cpu, src_cpu = smp_processor_id();
    unsigned long src_avg = src_data->ai_load / max(src_data->ai_task_count, 1);
    
    list_for_each_entry_safe(ai_task, tmp, &src_data->ai_tasks, list) {
        // Don't move real-time tasks
        if (ai_task->real_time)
            continue;
        
        // Find less loaded CPU
        for_each_online_cpu(dst_cpu) {
            if (dst_cpu == src_cpu)
                continue;
            
            dst_data = per_cpu_ptr(dst_cpu, cpu_data);
            if (dst_data->ai_task_count == 0 ||
                (dst_data->ai_load / max(dst_data->ai_task_count, 1)) < src_avg) {
                
                // Move task
                list_del(&ai_task->list);
                src_data->ai_task_count--;
                src_data->ai_load -= ai_task->estimated_runtime;
                
                spin_lock(&dst_data->lock);
                list_add_tail(&ai_task->list, &dst_data->ai_tasks);
                dst_data->ai_task_count++;
                dst_data->ai_load += ai_task->estimated_runtime;
                ai_task->preferred_cpu = dst_cpu;
                spin_unlock(&dst_data->lock);
                
                // Migrate task
                set_cpus_allowed_ptr(ai_task->task, cpumask_of(dst_cpu));
                
                pr_debug("Moved AI task %s from CPU %d to CPU %d\n",
                         ai_task->task->comm, src_cpu, dst_cpu);
                break;
            }
        }
    }
}

// Task scheduler hook
static void aurora_schedule_task(struct task_struct *task)
{
    // Check if this is an AI task
    if (!task)
        return;
    
    // Simple heuristic: check command name and properties
    if (strstr(task->comm, "python") || strstr(task->comm, "torch") ||
        strstr(task->comm, "tensor") || strstr(task->comm, "cuda") ||
        strstr(task->comm, "rocm") || strstr(task->comm, "opencl")) {
        
        if (!task->aurora_ai_tracked) {
            add_ai_task(task);
            task->aurora_ai_tracked = true;
        }
    }
}

// CPU hotplug callback
static int aurora_cpu_callback(struct notifier_block *nfb,
                               unsigned long action, void *hcpu)
{
    unsigned int cpu = (unsigned long)hcpu;
    
    switch (action) {
    case CPU_ONLINE:
    case CPU_ONLINE_FROZEN:
        aurora_init_cpu(cpu);
        break;
    case CPU_DEAD:
    case CPU_DEAD_FROZEN:
        // Cleanup CPU data
        del_timer_sync(&per_cpu_ptr(cpu_data, cpu)->balance_timer);
        break;
    }
    
    return NOTIFY_OK;
}

// Proc filesystem interface
static int aurora_scheduler_show(struct seq_file *m, void *v)
{
    int cpu;
    struct aurora_cpu_data *data;
    
    seq_printf(m, "Aurora OS AI Scheduler Statistics\n");
    seq_printf(m, "==================================\n\n");
    
    seq_printf(m, "Total AI Tasks: %d\n", atomic_read(&total_ai_tasks));
    seq_printf(m, "Completed AI Tasks: %d\n", atomic_read(&completed_ai_tasks));
    seq_printf(m, "Missed Deadlines: %d\n\n", atomic_read(&missed_deadlines));
    
    seq_printf(m, "Per-CPU Statistics:\n");
    for_each_online_cpu(cpu) {
        data = per_cpu_ptr(cpu_data, cpu);
        seq_printf(m, "CPU %d: Tasks=%d, Load=%lu ms\n",
                   cpu, data->ai_task_count, data->ai_load);
    }
    
    return 0;
}

static int aurora_scheduler_open(struct inode *inode, struct file *file)
{
    return single_open(file, aurora_scheduler_show, NULL);
}

static const struct proc_ops aurora_scheduler_proc_ops = {
    .proc_open = aurora_scheduler_open,
    .proc_read = seq_read,
    .proc_lseek = seq_lseek,
    .proc_release = single_release,
};

// Scheduler initialization
static int __init aurora_scheduler_init(void)
{
    int cpu, ret;
    
    pr_info("Aurora OS AI-Aware Scheduler v1.0\n");
    
    // Allocate per-CPU data
    cpu_data = alloc_percpu(struct aurora_cpu_data);
    if (!cpu_data) {
        pr_err("Failed to allocate per-CPU scheduler data\n");
        return -ENOMEM;
    }
    
    // Initialize each CPU
    for_each_online_cpu(cpu) {
        aurora_init_cpu(cpu);
    }
    
    // Register CPU hotplug notifier
    ret = register_cpu_notifier(&aurora_cpu_notifier);
    if (ret) {
        pr_err("Failed to register CPU hotplug notifier\n");
        goto err_free_percpu;
    }
    
    // Create proc entries
    aurora_proc_dir = proc_mkdir("aurora", NULL);
    if (!aurora_proc_dir) {
        pr_err("Failed to create proc directory\n");
        ret = -ENOMEM;
        goto err_unregister_notifier;
    }
    
    aurora_scheduler_proc = proc_create("scheduler", 0444, aurora_proc_dir,
                                       &aurora_scheduler_proc_ops);
    if (!aurora_scheduler_proc) {
        pr_err("Failed to create scheduler proc entry\n");
        ret = -ENOMEM;
        goto err_remove_proc_dir;
    }
    
    pr_info("Aurora AI scheduler initialized successfully\n");
    return 0;
    
err_remove_proc_dir:
    proc_remove(aurora_proc_dir);
err_unregister_notifier:
    unregister_cpu_notifier(&aurora_cpu_notifier);
err_free_percpu:
    free_percpu(cpu_data);
    return ret;
}

static void __exit aurora_scheduler_exit(void)
{
    int cpu;
    
    pr_info("Aurora AI scheduler unloading...\n");
    
    // Remove proc entries
    proc_remove(aurora_scheduler_proc);
    proc_remove(aurora_proc_dir);
    
    // Unregister notifier
    unregister_cpu_notifier(&aurora_cpu_notifier);
    
    // Cleanup per-CPU data
    for_each_online_cpu(cpu) {
        del_timer_sync(&per_cpu_ptr(cpu_data, cpu)->balance_timer);
    }
    
    free_percpu(cpu_data);
    
    pr_info("Aurora AI scheduler unloaded\n");
}

module_init(aurora_scheduler_init);
module_exit(aurora_scheduler_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Aurora OS Development Team");
MODULE_DESCRIPTION("Aurora OS AI-Aware Process Scheduler");
MODULE_VERSION("1.0");