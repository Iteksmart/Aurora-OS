/*
 * Aurora Application Launcher
 * Modern application launcher with Aurora Glass theme and AI integration
 * 
 * Copyright (c) 2024 Aurora-OS Enterprises
 * License: Aurora-OS Enterprise License
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/list.h>
#include <linux/hashtable.h>
#include <linux/delay.h>

#include "../include/aurora_desktop.h"
#include "../include/desktop_launcher.h"
#include "../include/desktop_theme.h"
#include "../../runtime/include/aurora_runtime.h"

#define LAUNCHER_VERSION "1.0.0"
#define LAUNCHER_MAX_APPS 1024
#define LAUNCHER_SEARCH_TIMEOUT_MS 500
#define LAUNCHER_ANIMATION_MS 300

/* Application launcher state */
struct aurora_launcher {
    struct mutex lock;
    struct list_head applications;
    struct list_head categories;
    struct list_head recent_apps;
    struct list_head favorite_apps;
    
    /* Search and filtering */
    char search_query[256];
    struct list_head search_results;
    u64 search_timestamp;
    
    /* AI integration */
    struct list_head recommended_apps;
    u64 last_recommendation_update;
    bool ai_enabled;
    
    /* Aurora Glass theme */
    struct aurora_theme *theme;
    bool glass_effects_enabled;
    u32 blur_radius;
    u32 transparency_level;
    
    /* Performance */
    atomic_t app_count;
    atomic_t search_count;
    ktime_t last_search_time;
    
    /* User preferences */
    char preferred_view_mode[32];  /* grid, list, compact */
    bool show_recent;
    bool show_favorites;
    bool show_recommendations;
    int apps_per_row;
};

static struct aurora_launcher aurora_launcher;

/* Application entry structure */
struct launcher_app {
    u64 app_id;
    char name[256];
    char description[512];
    char icon_path[512];
    char exec_path[1024];
    char category[64];
    char keywords[256];
    
    /* Usage statistics */
    u64 launch_count;
    ktime_t last_launched;
    ktime_t total_runtime;
    
    /* AI data */
    int ai_score;          /* AI recommendation score */
    float usage_frequency; /* Calculated usage frequency */
    
    /* Theme integration */
    u32 primary_color;
    u32 secondary_color;
    char custom_icon_path[512];
    
    struct list_head list;
    struct hlist_node hash;  /* Fast lookup by name */
};

/* Application category */
struct launcher_category {
    char name[64];
    char icon_path[512];
    u32 color;
    int app_count;
    struct list_head apps;
    struct list_head list;
};

/* Search result */
struct launcher_search_result {
    struct launcher_app *app;
    int relevance_score;
    int match_type;  /* name, category, keyword, description */
    struct list_head list;
};

/* AI recommendation */
struct launcher_recommendation {
    struct launcher_app *app;
    float confidence;
    char reason[256];
    ktime_t timestamp;
    struct list_head list;
};

/* Forward declarations */
static int __init launcher_init(void);
static void __exit launcher_exit(void);
static int launcher_open(struct inode *inode, struct file *file);
static int launcher_release(struct inode *inode, struct file *file);
static ssize_t launcher_read(struct file *file, char __user *buffer, size_t count, loff_t *pos);
static ssize_t launcher_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos);
static long launcher_ioctl(struct file *file, unsigned int cmd, unsigned long arg);

/* File operations */
static const struct file_operations launcher_fops = {
    .owner = THIS_MODULE,
    .open = launcher_open,
    .release = launcher_release,
    .read = launcher_read,
    .write = launcher_write,
    .unlocked_ioctl = launcher_ioctl,
    .llseek = no_llseek,
};

/* Hash table for fast app lookup */
DEFINE_HASHTABLE(app_hash_table, 8);

/* Initialize application launcher */
static int init_launcher_system(void)
{
    mutex_init(&aurora_launcher.lock);
    INIT_LIST_HEAD(&aurora_launcher.applications);
    INIT_LIST_HEAD(&aurora_launcher.categories);
    INIT_LIST_HEAD(&aurora_launcher.recent_apps);
    INIT_LIST_HEAD(&aurora_launcher.favorite_apps);
    INIT_LIST_HEAD(&aurora_launcher.search_results);
    INIT_LIST_HEAD(&aurora_launcher.recommended_apps);
    
    atomic_set(&aurora_launcher.app_count, 0);
    atomic_set(&aurora_launcher.search_count, 0);
    
    /* Set default preferences */
    strcpy(aurora_launcher.preferred_view_mode, "grid");
    aurora_launcher.show_recent = true;
    aurora_launcher.show_favorites = true;
    aurora_launcher.show_recommendations = true;
    aurora_launcher.apps_per_row = 6;
    aurora_launcher.ai_enabled = true;
    
    /* Initialize Aurora Glass theme */
    aurora_launcher.blur_radius = 15;
    aurora_launcher.transparency_level = 90;
    aurora_launcher.glass_effects_enabled = true;
    
    /* Initialize hash table */
    hash_init(app_hash_table);
    
    return 0;
}

/* Load system applications */
static int load_system_applications(void)
{
    struct launcher_app *app;
    int app_count = 0;
    
    /* Load desktop applications */
    app = launcher_create_app(
        "Aurora Files",
        "File manager with Aurora Glass theme",
        "/usr/share/icons/aurora/files.png",
        "/usr/bin/aurora-files",
        "System",
        "files,folder,manager,explorer"
    );
    if (app) {
        app->primary_color = 0x00D4FF;  /* Aurora cyan */
        launcher_add_app(app);
        app_count++;
    }
    
    /* Terminal */
    app = launcher_create_app(
        "Aurora Terminal",
        "Advanced terminal with AI assistance",
        "/usr/share/icons/aurora/terminal.png",
        "/usr/bin/aurora-terminal",
        "System",
        "terminal,console,shell,command"
    );
    if (app) {
        app->primary_color = 0xFF6B35;  /* Aurora orange */
        launcher_add_app(app);
        app_count++;
    }
    
    /* Web Browser */
    app = launcher_create_app(
        "Aurora Browser",
        "Web browser with security features",
        "/usr/share/icons/aurora/browser.png",
        "/usr/bin/aurora-browser",
        "Internet",
        "web,browser,internet,chrome,firefox"
    );
    if (app) {
        app->primary_color = 0x4CAF50;  /* Green */
        launcher_add_app(app);
        app_count++;
    }
    
    /* Settings */
    app = launcher_create_app(
        "Aurora Settings",
        "System settings and preferences",
        "/usr/share/icons/aurora/settings.png",
        "/usr/bin/aurora-settings",
        "System",
        "settings,preferences,config,control"
    );
    if (app) {
        app->primary_color = 0x2196F3;  /* Blue */
        launcher_add_app(app);
        app_count++;
    }
    
    /* Enterprise Console */
    app = launcher_create_app(
        "Enterprise Console",
        "Aurora-OS fleet management console",
        "/usr/share/icons/aurora/console.png",
        "/usr/bin/aurora-console",
        "Enterprise",
        "enterprise,console,management,admin"
    );
    if (app) {
        app->primary_color = 0x9C27B0;  /* Purple */
        launcher_add_app(app);
        app_count++;
    }
    
    printk(KERN_INFO "LAUNCHER: Loaded %d system applications\n", app_count);
    return app_count;
}

/* Load application categories */
static int load_app_categories(void)
{
    struct launcher_category *category;
    
    /* System */
    category = launcher_create_category("System", "/usr/share/icons/aurora/categories/system.png", 0x00D4FF);
    if (category) launcher_add_category(category);
    
    /* Internet */
    category = launcher_create_category("Internet", "/usr/share/icons/aurora/categories/internet.png", 0x4CAF50);
    if (category) launcher_add_category(category);
    
    /* Office */
    category = launcher_create_category("Office", "/usr/share/icons/aurora/categories/office.png", 0xFF9800);
    if (category) launcher_add_category(category);
    
    /* Graphics */
    category = launcher_create_category("Graphics", "/usr/share/icons/aurora/categories/graphics.png", 0xE91E63);
    if (category) launcher_add_category(category);
    
    /* Games */
    category = launcher_create_category("Games", "/usr/share/icons/aurora/categories/games.png", 0xFF5722);
    if (category) launcher_add_category(category);
    
    /* Development */
    category = launcher_create_category("Development", "/usr/share/icons/aurora/categories/development.png", 0x795548);
    if (category) launcher_add_category(category);
    
    /* Enterprise */
    category = launcher_create_category("Enterprise", "/usr/share/icons/aurora/categories/enterprise.png", 0x9C27B0);
    if (category) launcher_add_category(category);
    
    /* Multimedia */
    category = launcher_create_category("Multimedia", "/usr/share/icons/aurora/categories/multimedia.png", 0x00BCD4);
    if (category) launcher_add_category(category);
    
    return 0;
}

/* Search applications */
static int search_applications(const char *query)
{
    struct launcher_app *app;
    struct launcher_search_result *result;
    int matches = 0;
    ktime_t search_start, search_end;
    
    if (!query || strlen(query) == 0) {
        /* Clear search results */
        launcher_clear_search_results();
        strcpy(aurora_launcher.search_query, "");
        return 0;
    }
    
    search_start = ktime_get();
    
    /* Update search query */
    strscpy(aurora_launcher.search_query, query, sizeof(aurora_launcher.search_query));
    aurora_launcher.last_search_time = search_start;
    
    /* Clear previous results */
    launcher_clear_search_results();
    
    /* Search through applications */
    mutex_lock(&aurora_launcher.lock);
    list_for_each_entry(app, &aurora_launcher.applications, list) {
        int relevance = 0;
        int match_type = 0;
        
        /* Name matching (highest priority) */
        if (strncasecmp(app->name, query, strlen(query)) == 0) {
            relevance += 100;
            match_type = LAUNCHER_MATCH_NAME;
        } else if (strcasestr(app->name, query)) {
            relevance += 80;
            match_type = LAUNCHER_MATCH_NAME;
        }
        
        /* Category matching */
        if (strcasestr(app->category, query)) {
            relevance += 60;
            match_type = LAUNCHER_MATCH_CATEGORY;
        }
        
        /* Keywords matching */
        if (strcasestr(app->keywords, query)) {
            relevance += 40;
            match_type = LAUNCHER_MATCH_KEYWORD;
        }
        
        /* Description matching */
        if (strcasestr(app->description, query)) {
            relevance += 20;
            match_type = LAUNCHER_MATCH_DESCRIPTION;
        }
        
        /* Boost frequently used apps */
        if (app->launch_count > 0) {
            relevance += min(app->launch_count / 10, 20);
        }
        
        /* Boost recently used apps */
        if (app->last_launched > 0) {
            ktime_t time_diff = ktime_sub(ktime_get(), app->last_launched);
            s64 hours_ago = ktime_to_ns(time_diff) / (1000000000LL * 3600);
            if (hours_ago < 24) {
                relevance += 10;
            } else if (hours_ago < 168) {  /* 1 week */
                relevance += 5;
            }
        }
        
        if (relevance > 0) {
            result = kzalloc(sizeof(*result), GFP_KERNEL);
            if (result) {
                result->app = app;
                result->relevance_score = relevance;
                result->match_type = match_type;
                
                /* Insert in order of relevance */
                struct launcher_search_result *pos;
                list_for_each_entry(pos, &aurora_launcher.search_results, list) {
                    if (relevance > pos->relevance_score) {
                        list_add_tail(&result->list, &pos->list);
                        break;
                    }
                }
                if (list_empty(&result->list)) {
                    list_add_tail(&result->list, &aurora_launcher.search_results);
                }
                
                matches++;
            }
        }
    }
    mutex_unlock(&aurora_launcher.lock);
    
    search_end = ktime_get();
    atomic_inc(&aurora_launcher.search_count);
    
    if (matches > 0) {
        s64 search_time_ns = ktime_to_ns(ktime_sub(search_end, search_start));
        printk(KERN_DEBUG "LAUNCHER: Found %d matches for '%s' in %lld ns\n", 
               matches, query, search_time_ns);
    }
    
    return matches;
}

/* AI-powered application recommendations */
static int update_ai_recommendations(void)
{
    struct launcher_app *app;
    struct launcher_recommendation *recommendation;
    ktime_t current_time = ktime_get();
    int recommendations = 0;
    
    if (!aurora_launcher.ai_enabled) {
        return 0;
    }
    
    /* Update recommendations every 5 minutes */
    if (current_time - aurora_launcher.last_recommendation_update < 5 * 60 * 1000000000LL) {
        return 0;
    }
    
    /* Clear previous recommendations */
    launcher_clear_recommendations();
    
    mutex_lock(&aurora_launcher.lock);
    list_for_each_entry(app, &aurora_launcher.applications, list) {
        float confidence = 0.0;
        char reason[256] = "";
        
        /* Calculate AI score based on various factors */
        
        /* Usage frequency factor */
        if (app->launch_count > 0) {
            float frequency = (float)app->launch_count / (app->total_runtime / 1000000000.0 + 1.0);
            confidence += min(frequency / 10.0, 0.4);
            snprintf(reason, sizeof(reason), "Frequently used (%d launches)", app->launch_count);
        }
        
        /* Time of day factor */
        struct tm tm;
        time64_to_tm(ktime_get_real_seconds(), 0, &tm);
        int hour = tm.tm_hour;
        
        /* Morning recommendations */
        if (hour >= 6 && hour <= 9) {
            if (strstr(app->keywords, "email") || strstr(app->name, "Terminal")) {
                confidence += 0.3;
                strcat(reason, ", good for morning");
            }
        }
        /* Work hours */
        else if (hour >= 9 && hour <= 17) {
            if (strstr(app->category, "Office") || strstr(app->category, "Development")) {
                confidence += 0.3;
                strcat(reason, ", work hours");
            }
        }
        /* Evening */
        else if (hour >= 18 && hour <= 22) {
            if (strstr(app->category, "Multimedia") || strstr(app->category, "Games")) {
                confidence += 0.3;
                strcat(reason, ", evening time");
            }
        }
        
        /* System health factor */
        if (strstr(app->category, "System") && 
            (current_time - app->last_launched > 7 * 24 * 60 * 60 * 1000000000LL)) {
            confidence += 0.2;
            strcat(reason, ", system maintenance");
        }
        
        /* Add confidence for AI-specific apps */
        if (strstr(app->name, "AI") || strstr(app->keywords, "artificial")) {
            confidence += 0.1;
            strcat(reason, ", AI-powered");
        }
        
        if (confidence >= 0.3) {
            recommendation = kzalloc(sizeof(*recommendation), GFP_KERNEL);
            if (recommendation) {
                recommendation->app = app;
                recommendation->confidence = confidence;
                strscpy(recommendation->reason, reason, sizeof(recommendation->reason));
                recommendation->timestamp = current_time;
                
                list_add_tail(&recommendation->list, &aurora_launcher.recommended_apps);
                app->ai_score = (int)(confidence * 100);
                recommendations++;
            }
        }
    }
    mutex_unlock(&aurora_launcher.lock);
    
    aurora_launcher.last_recommendation_update = current_time;
    
    printk(KERN_DEBUG "LAUNCHER: Generated %d AI recommendations\n", recommendations);
    return recommendations;
}

/* Launch application */
static int launch_application(struct launcher_app *app, const char *args)
{
    struct aurora_app_launch launch;
    char full_args[2048] = "";
    int ret;
    
    if (!app) {
        return -EINVAL;
    }
    
    printk(KERN_INFO "LAUNCHER: Launching application: %s\n", app->name);
    
    /* Prepare launch arguments */
    strscpy(launch.path, app->exec_path, sizeof(launch.path));
    
    if (args && strlen(args) > 0) {
        snprintf(full_args, sizeof(full_args), "%s %s", app->exec_path, args);
        strscpy(launch.path, full_args, sizeof(launch.path));
    }
    
    launch.arg_count = 0;
    launch.preferred_type = AURORA_APP_UNKNOWN;
    launch.compat_mode = AURORA_COMPAT_NATIVE;
    launch.security_level = AURORA_SECURITY_MEDIUM;
    launch.perf_profile = AURORA_PERF_BALANCED;
    launch.sandbox_enabled = true;
    
    /* Use Universal App Runtime to launch */
    ret = runtime_launch_application(NULL, &launch);
    
    if (ret == 0) {
        /* Update app statistics */
        app->launch_count++;
        app->last_launched = ktime_get();
        
        /* Add to recent apps */
        launcher_add_to_recent(app);
        
        printk(KERN_INFO "LAUNCHER: Successfully launched %s (launch #%lu)\n", 
               app->name, app->launch_count);
    } else {
        printk(KERN_ERR "LAUNCHER: Failed to launch %s: %d\n", app->name, ret);
    }
    
    return ret;
}

/* Device file operations implementation */
static int launcher_open(struct inode *inode, struct file *file)
{
    struct launcher_client *client;
    
    client = kzalloc(sizeof(*client), GFP_KERNEL);
    if (!client)
        return -ENOMEM;
    
    mutex_init(&client->lock);
    client->pid = current->pid;
    client->connected_at = ktime_get();
    
    file->private_data = client;
    
    return 0;
}

static int launcher_release(struct inode *inode, struct file *file)
{
    struct launcher_client *client = file->private_data;
    
    if (client) {
        kfree(client);
    }
    
    return 0;
}

static ssize_t launcher_read(struct file *file, char __user *buffer, size_t count, loff_t *pos)
{
    struct launcher_client *client = file->private_data;
    char *kbuf;
    ssize_t len = 0;
    
    if (!client)
        return -EINVAL;
    
    kbuf = kmalloc(PAGE_SIZE, GFP_KERNEL);
    if (!kbuf)
        return -ENOMEM;
    
    /* Return launcher data based on client request */
    len = launcher_get_data_for_client(client, kbuf, PAGE_SIZE);
    
    if (len > 0 && copy_to_user(buffer, kbuf, len)) {
        kfree(kbuf);
        return -EFAULT;
    }
    
    kfree(kbuf);
    return len;
}

static ssize_t launcher_write(struct file *file, const char __user *buffer, size_t count, loff_t *pos)
{
    struct launcher_client *client = file->private_data;
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
    
    /* Process launcher command */
    ret = launcher_process_command(client, kbuf, count);
    
    kfree(kbuf);
    
    return (ret == 0) ? count : ret;
}

static long launcher_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    struct launcher_client *client = file->private_data;
    int ret = 0;
    
    if (!client)
        return -EINVAL;
    
    switch (cmd) {
    case LAUNCHER_GET_APPS:
        ret = launcher_get_applications((void __user *)arg);
        break;
        
    case LAUNCHER_SEARCH_APPS:
        ret = launcher_search_apps_io((void __user *)arg);
        break;
        
    case LAUNCHER_LAUNCH_APP:
        ret = launcher_launch_app_io((void __user *)arg);
        break;
        
    case LAUNCHER_GET_RECOMMENDATIONS:
        update_ai_recommendations();
        ret = launcher_get_recommendations((void __user *)arg);
        break;
        
    case LAUNCHER_ADD_TO_FAVORITES:
        ret = launcher_add_to_favorites(arg);
        break;
        
    case LAUNCHER_REMOVE_FROM_FAVORITES:
        ret = launcher_remove_from_favorites(arg);
        break;
        
    case LAUNCHER_GET_RECENT:
        ret = launcher_get_recent_apps((void __user *)arg);
        break;
        
    case LAUNCHER_SET_PREFERENCES:
        ret = launcher_set_preferences((void __user *)arg);
        break;
        
    case LAUNCHER_GET_PREFERENCES:
        ret = launcher_get_preferences((void __user *)arg);
        break;
        
    default:
        ret = -ENOTTY;
    }
    
    return ret;
}

/* Module initialization */
static int __init launcher_init(void)
{
    int ret;
    
    printk(KERN_INFO "Aurora Application Launcher v%s initializing...\n", LAUNCHER_VERSION);
    
    /* Initialize launcher system */
    ret = init_launcher_system();
    if (ret) {
        printk(KERN_ERR "LAUNCHER: Failed to initialize launcher system\n");
        return ret;
    }
    
    /* Load system applications */
    ret = load_system_applications();
    if (ret < 0) {
        printk(KERN_ERR "LAUNCHER: Failed to load system applications\n");
        return ret;
    }
    
    /* Load categories */
    ret = load_app_categories();
    if (ret) {
        printk(KERN_ERR "LAUNCHER: Failed to load app categories\n");
        return ret;
    }
    
    /* Initialize AI recommendations */
    update_ai_recommendations();
    
    /* Create device file */
    ret = launcher_create_device_file();
    if (ret) {
        printk(KERN_ERR "LAUNCHER: Failed to create device file\n");
        return ret;
    }
    
    printk(KERN_INFO "LAUNCHER: Aurora Application Launcher initialized successfully\n");
    printk(KERN_INFO "LAUNCHER: Loaded %d applications, %d categories\n", 
           atomic_read(&aurora_launcher.app_count), ret);
    printk(KERN_INFO "LAUNCHER: Aurora Glass theme: %s, AI recommendations: %s\n",
           aurora_launcher.glass_effects_enabled ? "enabled" : "disabled",
           aurora_launcher.ai_enabled ? "enabled" : "disabled");
    
    return 0;
}

static void __exit launcher_exit(void)
{
    printk(KERN_INFO "LAUNCHER: Aurora Application Launcher shutting down...\n");
    
    /* Cleanup launcher resources */
    launcher_cleanup();
    
    printk(KERN_INFO "LAUNCHER: Aurora Application Launcher shutdown complete\n");
}

/* Module information */
MODULE_LICENSE("Aurora-OS Enterprise License");
MODULE_AUTHOR("Aurora-OS Development Team");
MODULE_DESCRIPTION("Aurora Application Launcher - Modern Launcher with AI Integration");
MODULE_VERSION(LAUNCHER_VERSION);

MODULE_INFO(intree, "Y");
MODULE_INFO(staging, "Y");

module_init(launcher_init);
module_exit(launcher_exit);