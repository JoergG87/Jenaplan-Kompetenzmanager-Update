// Read-only status probe. Never queries, writes, unlocks, or deletes Keychain items.
#import <Foundation/Foundation.h>
#import <Security/Security.h>

int main(int argc, const char **argv) {
    @autoreleasepool {
        if (argc != 2) return 2;
        NSMutableDictionary *report = [NSMutableDictionary dictionary];
        SecKeychainRef keychain = NULL;
        OSStatus status = SecKeychainCopyDefault(&keychain);
        report[@"default_keychain_status"] = @(status);
        if (status == errSecSuccess && keychain != NULL) {
            SecKeychainStatus flags = 0;
            status = SecKeychainGetStatus(keychain, &flags);
            report[@"keychain_state_status"] = @(status);
            if (status == errSecSuccess) {
                report[@"unlocked"] = @((flags & kSecUnlockStateStatus) != 0);
                report[@"read_permission"] = @((flags & kSecReadPermStatus) != 0);
                report[@"write_permission"] = @((flags & kSecWritePermStatus) != 0);
            }
            CFRelease(keychain);
        }
        SecTrustedApplicationRef application = NULL;
        status = SecTrustedApplicationCreateFromPath(argv[1], &application);
        report[@"trusted_application_status"] = @(status);
        if (status == errSecSuccess && application != NULL) {
            const void *values[] = {application};
            CFArrayRef applications = CFArrayCreate(NULL, values, 1, &kCFTypeArrayCallBacks);
            SecAccessRef access = NULL;
            status = SecAccessCreate(CFSTR("JKM Read-only Diagnose"), applications, &access);
            report[@"access_descriptor_status"] = @(status);
            if (access) CFRelease(access);
            CFRelease(applications);
            CFRelease(application);
        }
        NSData *json = [NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingSortedKeys error:nil];
        puts([[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding].UTF8String);
        return [report[@"default_keychain_status"] isEqual:@0]
            && [report[@"keychain_state_status"] isEqual:@0]
            && [report[@"trusted_application_status"] isEqual:@0]
            && [report[@"access_descriptor_status"] isEqual:@0] ? 0 : 1;
    }
}
