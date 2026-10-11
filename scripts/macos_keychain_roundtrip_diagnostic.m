// Standalone synthetic test; no product application, database paths or item identifiers.
#import <AppKit/AppKit.h>
#import <Security/Security.h>
#include <fcntl.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

static void clear_bytes(void *buffer, size_t length) {
    volatile uint8_t *bytes = buffer;
    while (length--) *bytes++ = 0;
}

static NSDictionary *roundtrip(NSString *service) {
    NSMutableDictionary *report = [NSMutableDictionary dictionary];
    SecTrustedApplicationRef application = NULL;
    OSStatus status = SecTrustedApplicationCreateFromPath(NULL, &application);
    report[@"trusted_application_status"] = @(status);
    if (status != errSecSuccess || application == NULL) return report;
    const void *values[] = {application};
    CFArrayRef applications = CFArrayCreate(NULL, values, 1, &kCFTypeArrayCallBacks);
    CFRelease(application);
    SecAccessRef access = NULL;
    status = SecAccessCreate(CFSTR("JKM synthetische Diagnose"), applications, &access);
    CFRelease(applications);
    report[@"access_descriptor_status"] = @(status);
    if (status != errSecSuccess || access == NULL) return report;
    uint8_t secret[32] = {0};
    status = SecRandomCopyBytes(kSecRandomDefault, sizeof(secret), secret);
    report[@"random_status"] = @(status);
    if (status != errSecSuccess) { clear_bytes(secret, sizeof(secret)); CFRelease(access); return report; }
    NSDictionary *base = @{
        (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
        (__bridge id)kSecAttrService: [@"de.jenaplan.kompetenzmanager.keychain-diagnostic." stringByAppendingString:service],
        (__bridge id)kSecAttrAccount: @"synthetic-diagnostic",
    };
    NSMutableDictionary *query = [base mutableCopy];
    NSMutableData *data = [NSMutableData dataWithBytes:secret length:sizeof(secret)];
    clear_bytes(secret, sizeof(secret));
    query[(__bridge id)kSecValueData] = data;
    query[(__bridge id)kSecAttrAccess] = (__bridge id)access;
    status = SecItemAdd((__bridge CFDictionaryRef)query, NULL);
    CFRelease(access);
    report[@"item_add_status"] = @(status);
    if (status == errSecSuccess) {
        NSMutableDictionary *read = [base mutableCopy];
        read[(__bridge id)kSecMatchLimit] = (__bridge id)kSecMatchLimitOne;
        read[(__bridge id)kSecReturnData] = @YES;
        CFTypeRef result = NULL;
        status = SecItemCopyMatching((__bridge CFDictionaryRef)read, &result);
        report[@"item_read_status"] = @(status);
        if (status == errSecSuccess && result != NULL) {
            NSData *loaded = CFBridgingRelease(result);
            report[@"secret_matches"] = @([loaded isEqualToData:data]);
        } else if (result != NULL) { CFRelease(result); }
        report[@"item_delete_status"] = @(SecItemDelete((__bridge CFDictionaryRef)base));
    }
    clear_bytes(data.mutableBytes, data.length);
    return report;
}

int main(int argc, const char **argv) {
    @autoreleasepool {
        BOOL gui = argc == 1;
        NSString *directory = gui ? [NSBundle.mainBundle objectForInfoDictionaryKey:@"JKMDiagnosticReportDirectory"]
                                  : (argc == 3 && strcmp(argv[1], "--report") == 0 ? @(argv[2]) : nil);
        if (![directory isKindOfClass:NSString.class]) return 2;
        char rootPath[PATH_MAX], temporaryPath[PATH_MAX];
        if (!realpath(directory.fileSystemRepresentation, rootPath)
            || !realpath(NSTemporaryDirectory().fileSystemRepresentation, temporaryPath)) return 2;
        NSString *canonical = @(rootPath);
        NSString *temporary = @(temporaryPath);
        struct stat metadata;
        if (![directory isEqualToString:canonical]
            || ![canonical.stringByDeletingLastPathComponent isEqualToString:temporary]
            || ![canonical.lastPathComponent hasPrefix:@"jkm-keychain-roundtrip-"]
            || lstat(canonical.fileSystemRepresentation, &metadata) != 0
            || !S_ISDIR(metadata.st_mode) || metadata.st_uid != getuid() || (metadata.st_mode & 077)) return 2;
        NSArray *entries = [NSFileManager.defaultManager contentsOfDirectoryAtPath:canonical error:nil];
        if (entries == nil || (gui
            ? (entries.count != 1 || ![entries[0] isEqualToString:@"JKM-Schluesselbund-Diagnose.app"])
            : entries.count != 0)) return 2;
        NSString *reportPath = [directory stringByAppendingPathComponent:@"report.json"];
        int fd = open(reportPath.fileSystemRepresentation, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
        if (fd < 0) return 2;
        if (gui) {
            [NSApplication sharedApplication];
            [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
            [NSApp finishLaunching];
        }
        // Persist the exact unique synthetic identity before any item mutation.
        // A failed cleanup/crash remains recoverable without searching product items.
        NSString *identity = NSUUID.UUID.UUIDString;
        NSDictionary *authority = @{
            @"service": [@"de.jenaplan.kompetenzmanager.keychain-diagnostic." stringByAppendingString:identity],
            @"account": @"synthetic-diagnostic", @"state": @"prepared"
        };
        NSData *prepared = [NSJSONSerialization dataWithJSONObject:authority options:NSJSONWritingSortedKeys error:nil];
        if (prepared == nil || write(fd, prepared.bytes, prepared.length) != (ssize_t)prepared.length || fsync(fd) != 0) {
            close(fd); return 2;
        }
        int rootFd = open(directory.fileSystemRepresentation, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
        if (rootFd < 0 || fsync(rootFd) != 0) {
            if (rootFd >= 0) close(rootFd);
            close(fd); return 2;
        }
        close(rootFd);
        NSMutableDictionary *report = [roundtrip(identity) mutableCopy];
        [report addEntriesFromDictionary:authority];
        BOOL success = [report[@"item_add_status"] isEqual:@0]
            && [report[@"item_read_status"] isEqual:@0]
            && [report[@"secret_matches"] isEqual:@YES]
            && [report[@"item_delete_status"] isEqual:@0];
        report[@"state"] = success ? @"complete" : @"failed";
        report[@"success"] = @(success);
        // Keep the durable identity even if final JSON publication fails.
        NSString *finalPath = [directory stringByAppendingPathComponent:@"result.json"];
        close(fd);
        fd = open(finalPath.fileSystemRepresentation, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
        if (fd < 0) return 2;
        NSData *json = [NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingSortedKeys error:nil];
        BOOL saved = json != nil && write(fd, json.bytes, json.length) == (ssize_t)json.length && fsync(fd) == 0;
        close(fd);
        if (!saved) return 2;
        if (gui) {
            NSAlert *alert = [[NSAlert alloc] init];
            alert.messageText = @"Isolierte Schlüsselbundprüfung";
            alert.informativeText = [NSString stringWithFormat:@"Testschlüssel anlegen: %@\nLesen: %@\nInhalt stimmt überein: %@\nAufräumen: %@",
                report[@"item_add_status"] ?: @"nicht erreicht", report[@"item_read_status"] ?: @"nicht erreicht", report[@"secret_matches"] ?: @"nicht erreicht", report[@"item_delete_status"] ?: @"nicht erreicht"];
            [alert addButtonWithTitle:@"Schließen"];
            [alert runModal];
        }
        return success ? 0 : 1;
    }
}
