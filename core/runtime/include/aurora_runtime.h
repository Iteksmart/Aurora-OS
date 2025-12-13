/*
 * Aurora Universal App Runtime - Main Header
 * Cross-platform application compatibility definitions
 */

#ifndef _AURORA_RUNTIME_H
#define _AURORA_RUNTIME_H

#include <linux/types.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/mutex.h>
#include <linux/list.h>
#include <linux/uidgid.h>
#include <linux/ktime.h>
#include <linux/binfmts.h>
#include <linux/elf.h>

/* Runtime Version Information */
#define RUNTIME_VERSION_MAJOR 1
#define RUNTIME_VERSION_MINOR 0
#define RUNTIME_VERSION_PATCH 0
#define RUNTIME_VERSION_STRING "1.0.0"

/* Runtime Device Constants */
#define RUNTIME_MAX_CLIENTS 256
#define RUNTIME_MAX_APPS 1024
#define RUNTIME_MAX_PATH 4096
#define RUNTIME_MAX_ARGS 64
#define RUNTIME_MAX_ENV 256

/* Application Types */
enum aurora_app_type {
    AURORA_APP_UNKNOWN = 0,
    AURORA_APP_WINDOWS,
    AURORA_APP_LINUX_NATIVE,
    AURORA_APP_LINUX_COMPAT,
    AURORA_APP_WEB,
    AURORA_APP_AI,
    AURORA_APP_CONTAINER,
    AURORA_APP_SANDBOXED
};

/* Compatibility Modes */
enum aurora_compat_mode {
    AURORA_COMPAT_NATIVE = 0,
    AURORA_COMPAT_WINE,
    AURORA_COMPAT_EMULATION,
    AURORA_COMPAT_TRANSLATION,
    AURORA_COMPAT_VIRTUALIZATION,
    AURORA_COMPAT_HYBRID
};

/* Application Status */
enum aurora_app_status {
    AURORA_APP_PENDING = 0,
    AURORA_APP_LOADING,
    AURORA_APP_RUNNING,
    AURORA_APP_PAUSED,
    AURORA_APP_SUSPENDED,
    AURORA_APP_TERMINATED,
    AURORA_APP_CRASHED,
    AURORA_APP_ERROR
};

/* Security Levels */
enum aurora_security_level {
    AURORA_SECURITY_UNTRUSTED = 0,
    AURORA_SECURITY_LOW,
    AURORA_SECURITY_MEDIUM,
    AURORA_SECURITY_HIGH,
    AURORA_SECURITY_TRUSTED,
    AURORA_SECURITY_SYSTEM
};

/* Performance Profiles */
enum aurora_perf_profile {
    AURORA_PERF_POWER_SAVE = 0,
    AURORA_PERF_BALANCED,
    AURORA_PERF_PERFORMANCE,
    AURORA_PERF_HIGH_PERFORMANCE,
    AURORA_PERF_TURBO
};

/* Aurora Application Structure */
struct aurora_app {
    u64 app_id;
    u32 pid;
    u32 ppid;
    kuid_t uid;
    kgid_t gid;
    
    enum aurora_app_type type;
    enum aurora_app_status status;
    enum aurora_compat_mode compat_mode;
    enum aurora_security_level security_level;
    enum aurora_perf_profile perf_profile;
    
    char name[256];
    char path[RUNTIME_MAX_PATH];
    char args[RUNTIME_MAX_ARGS][256];
    char env[RUNTIME_MAX_ENV][512];
    int arg_count;
    int env_count;
    
    ktime_t start_time;
    ktime_t last_activity;
    ktime_t cpu_time;
    u64 memory_usage;
    u64 disk_io;
    u64 network_io;
    
    struct list_head list;
    struct mutex lock;
    
    /* Runtime specific data */
    void *runtime_data;
    size_t runtime_data_size;
    
    /* Security context */
    struct aurora_security_context *security_ctx;
    
    /* Performance metrics */
    struct aurora_perf_metrics *perf_metrics;
};

/* Runtime Client Structure */
struct runtime_client {
    u32 pid;
    uid_t uid;
    u32 permissions;
    struct mutex lock;
    struct list_head applications;
    struct list_head list;
    
    /* Statistics */
    u64 apps_launched;
    u64 apps_terminated;
    ktime_t connected_at;
    ktime_t last_activity;
    
    /* Preferences */
    enum aurora_compat_mode default_compat_mode;
    enum aurora_security_level default_security_level;
    enum aurora_perf_profile default_perf_profile;
};

/* Security Context */
struct aurora_security_context {
    u64 context_id;
    enum aurora_security_level level;
    bool sandbox_enabled;
    bool network_access;
    bool filesystem_access;
    bool system_call_filtering;
    bool memory_protection;
    
    /* Allowed operations */
    u64 allowed_syscalls[64];
    int allowed_syscall_count;
    
    /* Filesystem restrictions */
    char allowed_paths[64][RUNTIME_MAX_PATH];
    int allowed_path_count;
    
    /* Network restrictions */
    char allowed_hosts[32][256];
    int allowed_host_count;
    u16 allowed_ports[32];
    int allowed_port_count;
};

/* Performance Metrics */
struct aurora_perf_metrics {
    u64 cpu_usage_percent;
    u64 memory_usage_mb;
    u64 disk_read_mb;
    u64 disk_write_mb;
    u64 network_recv_mb;
    u64 network_sent_mb;
    u64 context_switches;
    u64 page_faults;
    u64 syscalls;
    
    ktime_t last_update;
    ktime_t avg_response_time;
    u64 peak_memory;
    u64 peak_cpu;
};

/* Runtime Statistics */
struct runtime_stats {
    u64 windows_apps_launched;
    u64 linux_apps_launched;
    u64 web_apps_launched;
    u64 ai_apps_launched;
    u64 compatibility_successes;
    u64 compatibility_failures;
    u64 sandbox_violations;
    u64 performance_optimizations;
    u64 avg_startup_time_ms;
    u64 security_blocks;
    u64 total_apps;
    u64 active_apps;
};

/* IOCTL Commands */
#define RUNTIME_MAGIC 'R'
#define RUNTIME_GET_STATS _IOR(RUNTIME_MAGIC, 1, struct runtime_stats)
#define RUNTIME_LAUNCH_APP _IOW(RUNTIME_MAGIC, 2, struct aurora_app_launch)
#define RUNTIME_KILL_APP _IOW(RUNTIME_MAGIC, 3, u64)
#define RUNTIME_GET_APP_INFO _IOR(RUNTIME_MAGIC, 4, struct aurora_app)
#define RUNTIME_SET_COMPAT_MODE _IOW(RUNTIME_MAGIC, 5, enum aurora_compat_mode)
#define RUNTIME_GET_COMPAT_MODE _IOR(RUNTIME_MAGIC, 6, enum aurora_compat_mode)
#define RUNTIME_SANDBOX_APP _IOW(RUNTIME_MAGIC, 7, struct aurora_security_context)
#define RUNTIME_OPTIMIZE_APP _IOW(RUNTIME_MAGIC, 8, u64)
#define RUNTIME_GET_PERF_METRICS _IOR(RUNTIME_MAGIC, 9, struct aurora_perf_metrics)
#define RUNTIME_SET_PERF_PROFILE _IOW(RUNTIME_MAGIC, 10, enum aurora_perf_profile)
#define RUNTIME_RESET_STATS _IO(RUNTIME_MAGIC, 11)

/* Application Launch Structure */
struct aurora_app_launch {
    char path[RUNTIME_MAX_PATH];
    char args[RUNTIME_MAX_ARGS][256];
    char env[RUNTIME_MAX_ENV][512];
    int arg_count;
    int env_count;
    enum aurora_app_type preferred_type;
    enum aurora_compat_mode compat_mode;
    enum aurora_security_level security_level;
    enum aurora_perf_profile perf_profile;
    bool sandbox_enabled;
};

/* Compatibility Detection Structure */
struct aurora_compat_info {
    enum aurora_app_type detected_type;
    enum aurora_compat_mode recommended_mode;
    int confidence_score;  /* 0-100 */
    char description[512];
    char required_libs[32][256];
    int required_lib_count;
    char known_issues[16][512];
    int known_issue_count;
    bool requires_emulation;
    bool requires_virtualization;
};

/* Function Prototypes */
int runtime_init_wine(void);
void runtime_cleanup_wine(void);
int runtime_init_web(void);
void runtime_cleanup_web(void);
int runtime_init_ai(void);
void runtime_cleanup_ai(void);
int runtime_init_sandbox(void);
void runtime_cleanup_sandbox(void);

/* Application Management */
int runtime_launch_application(struct runtime_client *client, struct aurora_app_launch *launch);
int runtime_kill_application(struct runtime_client *client, u64 app_id);
int runtime_get_app_info(struct runtime_client *client, struct aurora_app *app);
int runtime_get_client_apps_status(struct runtime_client *client, char *buffer, size_t size);
void runtime_cleanup_client_apps(struct runtime_client *client);

/* Compatibility Detection */
bool runtime_is_windows_executable(struct file *file);
bool runtime_is_linux_executable(struct file *file);
bool runtime_is_web_app(const char *path);
int runtime_detect_compatibility(const char *path, struct aurora_compat_info *info);
int runtime_load_windows_app(struct linux_binprm *bprm);
int runtime_load_linux_app(struct linux_binprm *bprm);
int runtime_load_web_app(struct linux_binprm *bprm);

/* Command Processing */
int runtime_process_command(struct runtime_client *client, const char *command, size_t len);

/* Registry and State Management */
void runtime_update_app_registry(void);
void runtime_process_pending_checks(void);
void runtime_optimize_applications(void);
int runtime_set_compatibility_mode(struct runtime_client *client, unsigned long mode);
int runtime_get_compatibility_mode(struct runtime_client *client, void __user *arg);

/* Security Functions */
u32 runtime_determine_permissions(kuid_t uid);
int runtime_sandbox_application(struct runtime_client *client, struct aurora_security_context *ctx);
int runtime_check_security_policy(struct aurora_app *app, const char *operation);

/* Performance Functions */
int runtime_optimize_application(struct runtime_client *client, u64 app_id);
int runtime_set_performance_profile(struct aurora_app *app, enum aurora_perf_profile profile);
void runtime_update_performance_metrics(struct aurora_app *app);

/* Utility Functions */
u64 runtime_generate_app_id(void);
ktime_t runtime_get_current_time(void);
const char *runtime_app_type_to_string(enum aurora_app_type type);
const char *runtime_status_to_string(enum aurora_app_status status);
const char *runtime_compat_mode_to_string(enum aurora_compat_mode mode);

/* Wine-specific Functions */
int runtime_wine_load_executable(struct linux_binprm *bprm);
int runtime_wine_setup_environment(struct aurora_app *app);
int runtime_wine_emulate_syscall(struct aurora_app *app, int syscall, unsigned long args[]);

/* Web Runtime Functions */
int runtime_web_launch_app(const char *url, struct aurora_app *app);
int runtime_web_create_isolated_context(struct aurora_app *app);
int runtime_web_handle_security_restrictions(struct aurora_app *app);

/* AI Runtime Functions */
int runtime_ai_launch_app(const char *model_path, struct aurora_app *app);
int runtime_ai_inference_request(struct aurora_app *app, const void *input, size_t input_size, void **output, size_t *output_size);
int runtime_ai_optimize_model(struct aurora_app *app);

#endif /* _AURORA_RUNTIME_H */