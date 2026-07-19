#import <Foundation/Foundation.h>
#import <Sparkle/Sparkle.h>

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static SPUStandardUpdaterController *jkm_controller = nil;

int32_t jkm_sparkle_start(void) {
    @autoreleasepool {
        if (![NSThread isMainThread]) {
            return 2;
        }
        if (jkm_controller != nil) {
            return 0;
        }
        jkm_controller = [[SPUStandardUpdaterController alloc]
            initWithStartingUpdater:NO
            updaterDelegate:nil
            userDriverDelegate:nil];
        NSError *error = nil;
        if (![jkm_controller.updater startUpdater:&error]) {
            jkm_controller = nil;
            return 1;
        }
        jkm_controller.updater.automaticallyChecksForUpdates = NO;
        jkm_controller.updater.automaticallyDownloadsUpdates = NO;
        return 0;
    }
}

int32_t jkm_sparkle_can_check(void) {
    @autoreleasepool {
        if (![NSThread isMainThread] || jkm_controller == nil) {
            return 0;
        }
        return jkm_controller.updater.canCheckForUpdates ? 1 : 0;
    }
}

int32_t jkm_sparkle_check_for_updates(void) {
    @autoreleasepool {
        if (![NSThread isMainThread] || jkm_controller == nil ||
            !jkm_controller.updater.canCheckForUpdates) {
            return 1;
        }
        [jkm_controller checkForUpdates:nil];
        return 0;
    }
}

char *jkm_sparkle_last_check_date(void) {
    @autoreleasepool {
        if (![NSThread isMainThread] || jkm_controller == nil) {
            return NULL;
        }
        NSDate *date = jkm_controller.updater.lastUpdateCheckDate;
        if (date == nil) {
            return NULL;
        }
        NSISO8601DateFormatter *formatter = [[NSISO8601DateFormatter alloc] init];
        NSString *value = [formatter stringFromDate:date];
        const char *utf8 = value.UTF8String;
        if (utf8 == NULL) {
            return NULL;
        }
        return strdup(utf8);
    }
}

void jkm_sparkle_string_free(char *value) {
    if (value != NULL) {
        memset(value, 0, strlen(value));
        free(value);
    }
}
