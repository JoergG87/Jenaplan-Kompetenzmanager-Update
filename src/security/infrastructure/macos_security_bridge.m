#import <Foundation/Foundation.h>
#import <LocalAuthentication/LocalAuthentication.h>
#import <Security/Security.h>

#include <stdlib.h>
#include <string.h>

static NSDictionary *jkm_query(const char *service, const char *account) {
    NSString *serviceValue = [NSString stringWithUTF8String:service];
    NSString *accountValue = [NSString stringWithUTF8String:account];
    if (serviceValue == nil || accountValue == nil) {
        return nil;
    }
    return @{
        (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
        (__bridge id)kSecAttrService: serviceValue,
        (__bridge id)kSecAttrAccount: accountValue,
    };
}

static SecAccessRef jkm_current_application_access(void) {
    SecTrustedApplicationRef application = NULL;
    OSStatus status = SecTrustedApplicationCreateFromPath(NULL, &application);
    if (status != errSecSuccess || application == NULL) {
        return NULL;
    }
    const void *values[] = {application};
    CFArrayRef trustedApplications = CFArrayCreate(
        kCFAllocatorDefault,
        values,
        1,
        &kCFTypeArrayCallBacks
    );
    CFRelease(application);
    if (trustedApplications == NULL) {
        return NULL;
    }
    SecAccessRef access = NULL;
    status = SecAccessCreate(
        CFSTR("Jenaplan-Kompetenzmanager Geraeteanmeldung"),
        trustedApplications,
        &access
    );
    CFRelease(trustedApplications);
    return status == errSecSuccess ? access : NULL;
}

int32_t jkm_keychain_create(
    const char *service,
    const char *account,
    const uint8_t *secret,
    size_t secret_length
) {
    @autoreleasepool {
        NSDictionary *base = jkm_query(service, account);
        if (base == nil || secret == NULL || secret_length != 32) {
            return errSecParam;
        }
        SecAccessRef access = jkm_current_application_access();
        if (access == NULL) {
            return errSecAuthFailed;
        }
        NSMutableDictionary *query = [base mutableCopy];
        query[(__bridge id)kSecValueData] = [NSData dataWithBytes:secret length:secret_length];
        query[(__bridge id)kSecAttrAccess] = (__bridge id)access;
        OSStatus status = SecItemAdd((__bridge CFDictionaryRef)query, NULL);
        CFRelease(access);
        return (int32_t)status;
    }
}

int32_t jkm_keychain_read(
    const char *service,
    const char *account,
    uint8_t **secret,
    size_t *secret_length
) {
    @autoreleasepool {
        if (secret == NULL || secret_length == NULL) {
            return errSecParam;
        }
        *secret = NULL;
        *secret_length = 0;
        NSDictionary *base = jkm_query(service, account);
        if (base == nil) {
            return errSecParam;
        }
        NSMutableDictionary *query = [base mutableCopy];
        query[(__bridge id)kSecMatchLimit] = (__bridge id)kSecMatchLimitOne;
        query[(__bridge id)kSecReturnData] = @YES;
        CFTypeRef result = NULL;
        OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &result);
        if (status != errSecSuccess) {
            return (int32_t)status;
        }
        NSData *data = CFBridgingRelease(result);
        if (data.length != 32) {
            return errSecDecode;
        }
        uint8_t *copy = malloc(data.length);
        if (copy == NULL) {
            return errSecAllocate;
        }
        memcpy(copy, data.bytes, data.length);
        *secret = copy;
        *secret_length = data.length;
        return errSecSuccess;
    }
}

int32_t jkm_keychain_delete(const char *service, const char *account) {
    @autoreleasepool {
        NSDictionary *query = jkm_query(service, account);
        if (query == nil) {
            return errSecParam;
        }
        return (int32_t)SecItemDelete((__bridge CFDictionaryRef)query);
    }
}

int32_t jkm_anchor_create(
    const char *service,
    const char *account,
    const uint8_t *payload,
    size_t payload_length,
    const uint8_t *payload_digest,
    size_t digest_length
) {
    @autoreleasepool {
        NSDictionary *base = jkm_query(service, account);
        if (
            base == nil || payload == NULL || payload_length == 0 ||
            payload_length > 8192 || payload_digest == NULL || digest_length != 32
        ) {
            return errSecParam;
        }
        SecAccessRef access = jkm_current_application_access();
        if (access == NULL) {
            return errSecAuthFailed;
        }
        NSMutableDictionary *query = [base mutableCopy];
        query[(__bridge id)kSecValueData] = [NSData dataWithBytes:payload length:payload_length];
        query[(__bridge id)kSecAttrGeneric] = [NSData dataWithBytes:payload_digest length:digest_length];
        query[(__bridge id)kSecAttrSynchronizable] = @NO;
        query[(__bridge id)kSecAttrAccess] = (__bridge id)access;
        OSStatus status = SecItemAdd((__bridge CFDictionaryRef)query, NULL);
        CFRelease(access);
        return (int32_t)status;
    }
}

int32_t jkm_anchor_read(
    const char *service,
    const char *account,
    uint8_t **payload,
    size_t *payload_length
) {
    @autoreleasepool {
        if (payload == NULL || payload_length == NULL) {
            return errSecParam;
        }
        *payload = NULL;
        *payload_length = 0;
        NSDictionary *base = jkm_query(service, account);
        if (base == nil) {
            return errSecParam;
        }
        NSMutableDictionary *query = [base mutableCopy];
        query[(__bridge id)kSecAttrSynchronizable] = @NO;
        query[(__bridge id)kSecMatchLimit] = (__bridge id)kSecMatchLimitOne;
        query[(__bridge id)kSecReturnData] = @YES;
        CFTypeRef result = NULL;
        OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &result);
        if (status != errSecSuccess) {
            return (int32_t)status;
        }
        NSData *data = CFBridgingRelease(result);
        if (data.length == 0 || data.length > 8192) {
            return errSecDecode;
        }
        uint8_t *copy = malloc(data.length);
        if (copy == NULL) {
            return errSecAllocate;
        }
        memcpy(copy, data.bytes, data.length);
        *payload = copy;
        *payload_length = data.length;
        return errSecSuccess;
    }
}

int32_t jkm_anchor_update(
    const char *service,
    const char *account,
    const uint8_t *expected_digest,
    size_t expected_digest_length,
    const uint8_t *payload,
    size_t payload_length,
    const uint8_t *payload_digest,
    size_t digest_length
) {
    @autoreleasepool {
        NSDictionary *base = jkm_query(service, account);
        if (
            base == nil || expected_digest == NULL || expected_digest_length != 32 ||
            payload == NULL || payload_length == 0 || payload_length > 8192 ||
            payload_digest == NULL || digest_length != 32
        ) {
            return errSecParam;
        }
        NSMutableDictionary *query = [base mutableCopy];
        query[(__bridge id)kSecAttrSynchronizable] = @NO;
        query[(__bridge id)kSecAttrGeneric] = [NSData dataWithBytes:expected_digest length:expected_digest_length];
        NSDictionary *replacement = @{
            (__bridge id)kSecValueData: [NSData dataWithBytes:payload length:payload_length],
            (__bridge id)kSecAttrGeneric: [NSData dataWithBytes:payload_digest length:digest_length],
        };
        return (int32_t)SecItemUpdate(
            (__bridge CFDictionaryRef)query,
            (__bridge CFDictionaryRef)replacement
        );
    }
}

void jkm_secret_free(uint8_t *secret, size_t secret_length) {
    if (secret != NULL) {
        memset(secret, 0, secret_length);
        free(secret);
    }
}

static int32_t jkm_la_error(NSError *error) {
    if (error == nil || ![error.domain isEqualToString:LAErrorDomain]) {
        return 8;
    }
    switch ((LAError)error.code) {
        case LAErrorUserCancel: return 1;
        case LAErrorUserFallback: return 2;
        case LAErrorPasscodeNotSet:
        case LAErrorBiometryNotAvailable:
        case LAErrorNotInteractive:
        case LAErrorBiometryNotPaired:
        case LAErrorBiometryDisconnected: return 3;
        case LAErrorBiometryNotEnrolled: return 4;
        case LAErrorBiometryLockout: return 5;
        case LAErrorSystemCancel:
        case LAErrorAppCancel:
        case LAErrorInvalidContext: return 6;
        case LAErrorAuthenticationFailed: return 7;
        default: return 8;
    }
}

int32_t jkm_local_auth_availability(void) {
    @autoreleasepool {
        LAContext *context = [[LAContext alloc] init];
        NSError *error = nil;
        BOOL available = [context canEvaluatePolicy:LAPolicyDeviceOwnerAuthenticationWithBiometrics error:&error];
        if (available && context.biometryType == LABiometryTypeTouchID) {
            return 0;
        }
        if (available) {
            return 3;
        }
        return jkm_la_error(error);
    }
}

int32_t jkm_local_authenticate(const char *reason) {
    @autoreleasepool {
        NSString *reasonValue = [NSString stringWithUTF8String:reason];
        if (reasonValue == nil || reasonValue.length == 0) {
            return 8;
        }
        LAContext *context = [[LAContext alloc] init];
        context.localizedFallbackTitle = @"Passwort verwenden";
        NSError *availabilityError = nil;
        if (![context canEvaluatePolicy:LAPolicyDeviceOwnerAuthenticationWithBiometrics error:&availabilityError]) {
            return jkm_la_error(availabilityError);
        }
        if (context.biometryType != LABiometryTypeTouchID) {
            return 3;
        }
        dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
        __block int32_t result = 8;
        [context evaluatePolicy:LAPolicyDeviceOwnerAuthenticationWithBiometrics
               localizedReason:reasonValue
                         reply:^(BOOL success, NSError *error) {
            result = success ? 0 : jkm_la_error(error);
            dispatch_semaphore_signal(semaphore);
        }];
        dispatch_semaphore_wait(semaphore, DISPATCH_TIME_FOREVER);
        [context invalidate];
        return result;
    }
}
