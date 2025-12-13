/*
 * Aurora Sense - Real-time Kernel Observability
 * Advanced system monitoring and analytics engine
 * 
 * Copyright (c) 2024 Aurora-OS Enterprises
 * License: Aurora-OS Enterprise License
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/mutex.h>
#include <linux/workqueue.h>
#include <linux/interrupt.h>
#include <linux/notifier.h>
#include <linux/perf_event.h>
#include <linux/kprobes.h>
#include <linux/tracepoint.h>

#include "include/aurora_sense.h"
#include "include/sense_ebpf.h"
#include "include/sense_metrics.h"
#include "include/sense_analytics.h"
#include "include/sense_security.h"

#define SENSE_VERSION "1.0.0"
#define SENSE_DEVICE_NAME "aurora_sense"
#define SENSE_CLASS_NAME  "aurora"
#define SENSE_PROC_NAME   "aurora_sense"

/* Module parameters */
static bool debug_mode = true;
static bool enterprise_mode = true;
static bool fips_mode = false;
static int monitoring_interval_ms = 1000;  // 1-second default
static int metrics_retention_hours = 24;

module_param(debug_mode, bool, 0644);
MODULE_PARM_DESC(debug_mode, "Enable Sense debug mode");

module_param(enterprise_mode, bool, 0644);
MODULE_PARM_DESC(enterprise_mode, "Enable enterprise features");

module_param(fips_mode, bool, 0644);
MODULE_PARM_DESC(fips_mode, "Enable FIPS compliance mode");

module_param(monitoring_interval_ms, int, 0644);
MODULE_PARM_DESC(monitoring_interval_ms, "Metrics collection interval in milliseconds");

module_param(metrics_retention_hours, int, 0644);
MODULE_PARM_DESC(metrics_retention_hours, "Metrics retention period in hours");

/* Device and class structures */
static struct class *sense_class;
static struct device *sense_device;
static dev_t sense_dev_t;
static struct cdev sense_cdev;

/* Sense Core State */
struct sense_core_state {
    struct mutex state_lock;
    atomic_t metrics_count;
    atomic_t alerts_count;
    atomic_t probes_active;
    ktime_t start_time;
    ktime_t last_collection;
    bool initialized;
    bool active;
    bool monitoring_enabled;
};

static struct sense_core_state sense_state;

/* Work queue for metrics collection */
static struct workqueue_struct *sense_workqueue;
static struct delayed_work metrics_work;

/* Performance monitoring */
struct perf_event_attr sense_perf_attr;
static struct perf_event *sense_perf_events[MAX_PERF_EVENTS];
static int num_perf_events = 0;

/* Kprobe handles */
static struct kprobe sense_kprobes[MAX_KPROBES];
static int num_kprobes = 0;

/* Statistics */
struct sense_stats {
    u64 metrics_collected;
    u64 alerts_generated;
    u64 probes_triggered;
    u64 memory_usage_mb;
    u64 cpu_usage_percent;
    u64 network_bytes_tx;
    u64 network_bytes_rx;
    u64 disk_io_read_mb;
    u64 disk_io_write_mb;
    u64 security_events;
    u64 anomalies_detected;
};

static struct sense_stats sense_statistics;

/* Forward declarations */
static int __init sense_init(void);
static void __exit sense_exit(void);
static int sense_open(struct inode *inode, struct file *file);
static int sense_release(struct inode *inode, struct file *file);
static ssize_t sense_read(struct file *file, char __user *buffer, size_t count, loff_t *pos);
static ssize_t sense_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos);
static long sense_ioctl(struct file *file, unsigned int cmd, unsigned long arg);

/* File operations */
static const struct file_operations sense_fops = {
    .owner = THIS_MODULE,
    .open = sense_open,
    .release = sense_release,
    .read = sense_read,
    .write = sense_write,
    .unlocked_ioctl = sense_ioctl,
    .llseek = no_llseek,
};

/* Metrics collection work function */
static void sense_metrics_work_func(struct work_struct *work)
{
    ktime_t start_time, end_time;
    s64 duration_ns;
    
    start_time = ktime_get();
    
    if (debug_mode) {
        printk(KERN_DEBUG "SENSE: Collecting metrics\n");
    }
    
    /* Collect system metrics */
    sense_collect_cpu_metrics();
    sense_collect_memory_metrics();
    sense_collect_network_metrics();
    sense_collect_disk_metrics();
    sense_collect_process_metrics();
    
    /* Run analytics */
    sense_run_analytics();
    
    /* Check for anomalies */
    sense_detect_anomalies();
    
    /* Update statistics */
    end_time = ktime_get();
    duration_ns = ktime_to_ns(ktime_sub(end_time, start_time));
    
    atomic_inc(&sense_state.metrics_count);
    sense_state.last_collection = ktime_get();
    
    /* Schedule next collection */
    if (sense_state.monitoring_enabled) {
        schedule_delayed_work(&metrics_work, 
                            msecs_to_jiffies(monitoring_interval_ms));
    }
}

/* Device file operations */
static int sense_open(struct inode *inode, struct file *file)
{
    struct sense_client *client;
    
    client = kzalloc(sizeof(*client), GFP_KERNEL);
    if (!client)
        return -ENOMEM;
    
    mutex_init(&client->lock);
    client->pid = current->pid;
    client->uid = current_uid().val;
    client->access_level = sense_determine_access_level(current_uid());
    INIT_LIST_HEAD(&client->subscriptions);
    client->connected_at = ktime_get();
    
    file->private_data = client;
    
    if (debug_mode)
        printk(KERN_INFO "SENSE: Client opened (PID: %d, UID: %d, Level: %d)\n", 
               client->pid, client->uid, client->access_level);
    
    return 0;
}

static int sense_release(struct inode *inode, struct file *file)
{
    struct sense_client *client = file->private_data;
    
    if (client) {
        sense_cleanup_client_subscriptions(client);
        kfree(client);
    }
    
    if (debug_mode)
        printk(KERN_INFO "SENSE: Client released\n");
    
    return 0;
}

static ssize_t sense_read(struct file *file, char __user *buffer, size_t count, loff_t *pos)
{
    struct sense_client *client = file->private_data;
    char *kbuf;
    ssize_t len = 0;
    
    if (!client)
        return -EINVAL;
    
    kbuf = kmalloc(PAGE_SIZE, GFP_KERNEL);
    if (!kbuf)
        return -ENOMEM;
    
    /* Read subscribed metrics */
    len = sense_get_client_metrics(client, kbuf, PAGE_SIZE);
    
    if (len > 0 && copy_to_user(buffer, kbuf, len)) {
        kfree(kbuf);
        return -EFAULT;
    }
    
    kfree(kbuf);
    return len;
}

static ssize_t sense_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos)
{
    struct sense_client *client = file->private_data;
    char *kbuf;
    int ret;
    
    if (!client || !buffer || count == 0)
        return -EINVAL;
    
    if (count > PAGE_SIZE)
        count = PAGE_SIZE;
    
    kbuf = kmalloc(count + 1, GFP_KERNEL);
    if (!kbuf)
        return -ENOMEM;
    
    if (copy_from_user(kbuf, buffer, count)) {
        kfree(kbuf);
        return -EFAULT;
    }
    kbuf[count] = '\0';
    
    /* Process command or subscription */
    ret = sense_process_command(client, kbuf, count);
    
    kfree(kbuf);
    
    return (ret == 0) ? count : ret;
}

static long sense_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    struct sense_client *client = file->private_data;
    int ret = 0;
    
    if (!client)
        return -EINVAL;
    
    switch (cmd) {
    case SENSE_GET_STATS:
        if (copy_to_user((void __user *)arg, &sense_statistics, 
                        sizeof(sense_statistics)))
            ret = -EFAULT;
        break;
        
    case SENSE_SET_MONITORING:
        if (enterprise_mode && !capable(CAP_SYS_ADMIN)) {
            ret = -EPERM;
        } else {
            sense_set_monitoring_enabled(!!arg);
            ret = 0;
        }
        break;
        
    case SENSE_GET_METRICS:
        ret = sense_get_metrics_data((void __user *)arg);
        break;
        
    case SENSE_SUBSCRIBE_METRIC:
        ret = sense_subscribe_metric(client, arg);
        break;
        
    case SENSE_UNSUBSCRIBE_METRIC:
        ret = sense_unsubscribe_metric(client, arg);
        break;
        
    case SENSE_SET_INTERVAL:
        if (enterprise_mode && !capable(CAP_SYS_ADMIN)) {
            ret = -EPERM;
        } else {
            monitoring_interval_ms = arg;
            ret = 0;
        }
        break;
        
    case SENSE_RESET_STATS:
        if (capable(CAP_SYS_ADMIN)) {
            memset(&sense_statistics, 0, sizeof(sense_statistics));
            ret = 0;
        } else {
            ret = -EPERM;
        }
        break;
        
    default:
        ret = -ENOTTY;
    }
    
    return ret;
}

/* Performance event callback */
static void sense_perf_callback(struct perf_event *event, 
                               struct perf_sample_data *data,
                               struct pt_regs *regs)
{
    struct sense_perf_data *perf_data;
    
    perf_data = kzalloc(sizeof(*perf_data), GFP_ATOMIC);
    if (!perf_data)
        return;
    
    perf_data->event_type = event->attr.type;
    perf_data->event_config = event->attr.config;
    perf_data->timestamp = ktime_get();
    perf_data->cpu = smp_processor_id();
    perf_data->pid = current->pid;
    
    if (data) {
        perf_data->value = data->period;
        perf_data->addr = data->addr;
        perf_data->regs = regs;
    }
    
    /* Queue for processing */
    sense_queue_perf_data(perf_data);
}

/* Kprobe entry handler */
static int sense_kprobe_handler(struct kprobe *kp, struct pt_regs *regs)
{
    struct sense_kprobe_data *kp_data;
    
    kp_data = kzalloc(sizeof(*kp_data), GFP_ATOMIC);
    if (!kp_data)
        return 0;
    
    kp_data->kp = kp;
    kp_data->timestamp = ktime_get();
    kp_data->cpu = smp_processor_id();
    kp_data->pid = current->pid;
    kp_data->ip = regs->ip;
    
    /* Queue for processing */
    sense_queue_kprobe_data(kp_data);
    
    return 0;
}

/* Initialize performance monitoring */
static int sense_init_perf_events(void)
{
    int i;
    
    /* Initialize CPU cycle counter */
    memset(&sense_perf_attr, 0, sizeof(sense_perf_attr));
    sense_perf_attr.type = PERF_TYPE_HARDWARE;
    sense_perf_attr.config = PERF_COUNT_HW_CPU_CYCLES;
    sense_perf_attr.disabled = 1;
    sense_perf_attr.exclude_kernel = 0;
    sense_perf_attr.exclude_hv = 1;
    
    for (i = 0; i < num_online_cpus(); i++) {
        if (num_perf_events >= MAX_PERF_EVENTS)
            break;
            
        sense_perf_events[num_perf_events] = 
            perf_event_create_kernel_counter(&sense_perf_attr, i, NULL, 
                                           sense_perf_callback, NULL);
        
        if (IS_ERR(sense_perf_events[num_perf_events])) {
            printk(KERN_WARNING "SENSE: Failed to create perf event on CPU %d\n", i);
            continue;
        }
        
        /* Enable the event */
        perf_event_enable(sense_perf_events[num_perf_events]);
        num_perf_events++;
    }
    
    printk(KERN_INFO "SENSE: Initialized %d performance events\n", num_perf_events);
    return 0;
}

/* Initialize kprobes */
static int sense_init_kprobes(void)
{
    int ret, i = 0;
    
    /* Probe system calls */
    if (i < MAX_KPROBES) {
        sense_kprobes[i].symbol_name = "__do_sys_open";
        sense_kprobes[i].pre_handler = sense_kprobe_handler;
        ret = register_kprobe(&sense_kprobes[i]);
        if (ret == 0)
            i++;
        else
            printk(KERN_WARNING "SENSE: Failed to probe __do_sys_open: %d\n", ret);
    }
    
    /* Probe memory allocation */
    if (i < MAX_KPROBES) {
        sense_kprobes[i].symbol_name = "__kmalloc";
        sense_kprobes[i].pre_handler = sense_kprobe_handler;
        ret = register_kprobe(&sense_kprobes[i]);
        if (ret == 0)
            i++;
        else
            printk(KERN_WARNING "SENSE: Failed to probe __kmalloc: %d\n", ret);
    }
    
    /* Probe schedule function */
    if (i < MAX_KPROBES) {
        sense_kprobes[i].symbol_name = "schedule";
        sense_kprobes[i].pre_handler = sense_kprobe_handler;
        ret = register_kprobe(&sense_kprobes[i]);
        if (ret == 0)
            i++;
        else
            printk(KERN_WARNING "SENSE: Failed to probe schedule: %d\n", ret);
    }
    
    num_kprobes = i;
    printk(KERN_INFO "SENSE: Initialized %d kprobes\n", num_kprobes);
    return 0;
}

/* Cleanup performance monitoring */
static void sense_cleanup_perf_events(void)
{
    int i;
    
    for (i = 0; i < num_perf_events; i++) {
        if (sense_perf_events[i]) {
            perf_event_disable(sense_perf_events[i]);
            perf_event_release_kernel(sense_perf_events[i]);
        }
    }
    
    num_perf_events = 0;
}

/* Cleanup kprobes */
static void sense_cleanup_kprobes(void)
{
    int i;
    
    for (i = 0; i < num_kprobes; i++) {
        unregister_kprobe(&sense_kprobes[i]);
    }
    
    num_kprobes = 0;
}

/* Proc filesystem interface */
static int sense_proc_show(struct seq_file *m, void *v)
{
    seq_printf(m, "Aurora Sense v%s\n", SENSE_VERSION);
    seq_printf(m, "==========================\n");
    seq_printf(m, "Status: %s\n", sense_state.active ? "Active" : "Inactive");
    seq_printf(m, "Monitoring: %s\n", sense_state.monitoring_enabled ? "Enabled" : "Disabled");
    seq_printf(m, "Mode: %s\n", enterprise_mode ? "Enterprise" : "Standard");
    seq_printf(m, "FIPS Compliance: %s\n", fips_mode ? "Enabled" : "Disabled");
    seq_printf(m, "Collection Interval: %d ms\n", monitoring_interval_ms);
    seq_printf(m, "Retention Period: %d hours\n", metrics_retention_hours);
    seq_printf(m, "\nLive Statistics:\n");
    seq_printf(m, "  Metrics Collected: %llu\n", sense_statistics.metrics_collected);
    seq_printf(m, "  Alerts Generated: %llu\n", sense_statistics.alerts_generated);
    seq_printf(m, "  Probes Triggered: %llu\n", sense_statistics.probes_triggered);
    seq_printf(m, "  Memory Usage: %llu MB\n", sense_statistics.memory_usage_mb);
    seq_printf(m, "  CPU Usage: %llu%%\n", sense_statistics.cpu_usage_percent);
    seq_printf(m, "  Network TX: %llu bytes\n", sense_statistics.network_bytes_tx);
    seq_printf(m, "  Network RX: %llu bytes\n", sense_statistics.network_bytes_rx);
    seq_printf(m, "  Disk Read: %llu MB\n", sense_statistics.disk_io_read_mb);
    seq_printf(m, "  Disk Write: %llu MB\n", sense_statistics.disk_io_write_mb);
    seq_printf(m, "  Security Events: %llu\n", sense_statistics.security_events);
    seq_printf(m, "  Anomalies Detected: %llu\n", sense_statistics.anomalies_detected);
    seq_printf(m, "\nSystem Status:\n");
    seq_printf(m, "  Active Probes: %d\n", num_kprobes);
    seq_printf(m, "  Performance Events: %d\n", num_perf_events);
    seq_printf(m, "  Uptime: %lld seconds\n", 
               ktime_to_ms(ktime_sub(ktime_get(), sense_state.start_time)) / 1000);
    
    return 0;
}

static int sense_proc_open(struct inode *inode, struct file *file)
{
    return single_open(file, sense_proc_show, NULL);
}

static const struct proc_ops sense_proc_ops = {
    .proc_open = sense_proc_open,
    .proc_read = seq_read,
    .proc_lseek = seq_lseek,
    .proc_release = single_release,
};

/* Module initialization */
static int __init sense_init(void)
{
    int ret;
    
    printk(KERN_INFO "Aurora Sense v%s initializing...\n", SENSE_VERSION);
    
    /* Initialize core state */
    mutex_init(&sense_state.state_lock);
    atomic_set(&sense_state.metrics_count, 0);
    atomic_set(&sense_state.alerts_count, 0);
    atomic_set(&sense_state.probes_active, 0);
    sense_state.start_time = ktime_get();
    sense_state.last_collection = ktime_get();
    sense_state.initialized = false;
    sense_state.active = false;
    sense_state.monitoring_enabled = true;
    
    /* Create workqueue */
    sense_workqueue = create_singlethread_workqueue("sense_workqueue");
    if (!sense_workqueue) {
        printk(KERN_ERR "SENSE: Failed to create workqueue\n");
        return -ENOMEM;
    }
    
    INIT_DELAYED_WORK(&metrics_work, sense_metrics_work_func);
    
    /* Initialize subsystems */
    ret = sense_init_ebpf();
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to initialize eBPF subsystem\n");
        goto cleanup_workqueue;
    }
    
    ret = sense_init_metrics();
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to initialize metrics system\n");
        goto cleanup_ebpf;
    }
    
    ret = sense_init_analytics();
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to initialize analytics system\n");
        goto cleanup_metrics;
    }
    
    ret = sense_init_security();
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to initialize security system\n");
        goto cleanup_analytics;
    }
    
    /* Initialize monitoring infrastructure */
    ret = sense_init_perf_events();
    if (ret) {
        printk(KERN_WARNING "SENSE: Failed to initialize performance events\n");
    }
    
    ret = sense_init_kprobes();
    if (ret) {
        printk(KERN_WARNING "SENSE: Failed to initialize kprobes\n");
    }
    
    /* Create device class and device */
    sense_class = class_create(THIS_MODULE, SENSE_CLASS_NAME);
    if (IS_ERR(sense_class)) {
        ret = PTR_ERR(sense_class);
        printk(KERN_ERR "SENSE: Failed to create device class\n");
        goto cleanup_monitoring;
    }
    
    ret = alloc_chrdev_region(&sense_dev_t, 0, 1, SENSE_DEVICE_NAME);
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to allocate device number\n");
        goto cleanup_class;
    }
    
    cdev_init(&sense_cdev, &sense_fops);
    sense_cdev.owner = THIS_MODULE;
    
    ret = cdev_add(&sense_cdev, sense_dev_t, 1);
    if (ret) {
        printk(KERN_ERR "SENSE: Failed to add character device\n");
        goto cleanup_chrdev;
    }
    
    sense_device = device_create(sense_class, NULL, sense_dev_t, NULL, SENSE_DEVICE_NAME);
    if (IS_ERR(sense_device)) {
        ret = PTR_ERR(sense_device);
        printk(KERN_ERR "SENSE: Failed to create device\n");
        goto cleanup_cdev;
    }
    
    /* Create proc entry */
    proc_create(SENSE_PROC_NAME, 0444, NULL, &sense_proc_ops);
    
    /* Initialize statistics */
    memset(&sense_statistics, 0, sizeof(sense_statistics));
    
    /* Start metrics collection */
    schedule_delayed_work(&metrics_work, 
                         msecs_to_jiffies(monitoring_interval_ms));
    
    /* Mark as initialized and active */
    sense_state.initialized = true;
    sense_state.active = true;
    
    printk(KERN_INFO "SENSE: Aurora Sense initialized successfully\n");
    printk(KERN_INFO "SENSE: Enterprise mode: %s\n", enterprise_mode ? "enabled" : "disabled");
    printk(KERN_INFO "SENSE: FIPS compliance: %s\n", fips_mode ? "enabled" : "disabled");
    printk(KERN_INFO "SENSE: Monitoring interval: %d ms\n", monitoring_interval_ms);
    printk(KERN_INFO "SENSE: Metrics retention: %d hours\n", metrics_retention_hours);
    
    return 0;
    
cleanup_cdev:
    cdev_del(&sense_cdev);
cleanup_chrdev:
    unregister_chrdev_region(sense_dev_t, 1);
cleanup_class:
    class_destroy(sense_class);
cleanup_monitoring:
    sense_cleanup_kprobes();
    sense_cleanup_perf_events();
    sense_cleanup_security();
cleanup_analytics:
    sense_cleanup_analytics();
cleanup_metrics:
    sense_cleanup_metrics();
cleanup_ebpf:
    sense_cleanup_ebpf();
cleanup_workqueue:
    destroy_workqueue(sense_workqueue);
    
    return ret;
}

static void __exit sense_exit(void)
{
    printk(KERN_INFO "SENSE: Aurora Sense shutting down...\n");
    
    /* Stop monitoring */
    sense_state.monitoring_enabled = false;
    cancel_delayed_work_sync(&metrics_work);
    
    /* Mark as inactive */
    sense_state.active = false;
    
    /* Remove proc entry */
    remove_proc_entry(SENSE_PROC_NAME, NULL);
    
    /* Destroy device */
    device_destroy(sense_class, sense_dev_t);
    cdev_del(&sense_cdev);
    unregister_chrdev_region(sense_dev_t, 1);
    class_destroy(sense_class);
    
    /* Cleanup monitoring infrastructure */
    sense_cleanup_kprobes();
    sense_cleanup_perf_events();
    
    /* Cleanup subsystems */
    sense_cleanup_security();
    sense_cleanup_analytics();
    sense_cleanup_metrics();
    sense_cleanup_ebpf();
    
    /* Destroy workqueue */
    destroy_workqueue(sense_workqueue);
    
    printk(KERN_INFO "SENSE: Aurora Sense shutdown complete\n");
}

/* Module information */
MODULE_LICENSE("Aurora-OS Enterprise License");
MODULE_AUTHOR("Aurora-OS Development Team");
MODULE_DESCRIPTION("Aurora Sense - Real-time Kernel Observability System");
MODULE_VERSION(SENSE_VERSION);

MODULE_INFO(intree, "Y");
MODULE_INFO(staging, "Y");

module_init(sense_init);
module_exit(sense_exit);