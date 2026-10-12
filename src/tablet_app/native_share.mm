// Native presentation port. No data model, ratings or database logic.
#import <UIKit/UIKit.h>
#import <objc/runtime.h>
#include <Python.h>
#include <QtGui/QAccessible>
#include <QtCore/QCoreApplication>

// PO temporarily defers VoiceOver/accessibility for this isolated test build.
// The iOS Qt 6.12.0 accessibility bridge was verified to crash while deleting
// buttons. Suppress its construction/destruction callbacks in the test app.
// This does not change system settings or the desktop application's behavior.
static void tablet_test_accessibility_update(QAccessibleEvent *) {}
static id tablet_test_accessibility_elements(id, SEL) { return @[]; }
static PyObject *jkm_install_test_accessibility_mode(PyObject *, PyObject *)
{
    // Qt's QUIView automatically reactivates Qt accessibility when a client
    // asks for its elements. Keep this isolated test view from reactivating
    // the broken bridge; UIKit's native share sheet remains unaffected.
    Class viewClass = NSClassFromString(@"QUIView");
    Method elements = class_getInstanceMethod(viewClass, @selector(accessibilityElements));
    if (!elements) {
        PyErr_SetString(PyExc_RuntimeError, "Qt-iPad-Testmodus nicht verfügbar.");
        return nullptr;
    }
    method_setImplementation(elements, (IMP)tablet_test_accessibility_elements);
    QAccessible::setActive(false);
    QAccessible::installUpdateHandler(tablet_test_accessibility_update);
    Py_RETURN_NONE;
}

static PyObject *jkm_share_file(PyObject *, PyObject *args)
{
    const char *rawPath;
    if (!PyArg_ParseTuple(args, "s", &rawPath)) return nullptr;
    NSString *path = [[NSString stringWithUTF8String:rawPath] stringByStandardizingPath];
    NSString *root = [[NSTemporaryDirectory() stringByAppendingPathComponent:@"jkm-tablet-share"] stringByResolvingSymlinksInPath];
    NSString *resolved = [path stringByResolvingSymlinksInPath];
    BOOL isDirectory = NO;
    if (![resolved hasPrefix:[root stringByAppendingString:@"/"]] ||
        ![[resolved pathExtension] isEqualToString:@"pdf"] ||
        ![[NSFileManager defaultManager] fileExistsAtPath:resolved isDirectory:&isDirectory] || isDirectory ||
        ![path isEqualToString:resolved]) {
        PyErr_SetString(PyExc_ValueError, "Unsichere iPad-PDF-Ausgabe.");
        return nullptr;
    }
    UIWindow *window = nil;
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if ([scene isKindOfClass:UIWindowScene.class] && scene.activationState == UISceneActivationStateForegroundActive) {
            for (UIWindow *candidate in ((UIWindowScene *)scene).windows) {
                if (candidate.isKeyWindow) { window = candidate; break; }
            }
        }
    }
    UIViewController *controller = window.rootViewController;
    while (controller.presentedViewController) controller = controller.presentedViewController;
    if (!controller) {
        PyErr_SetString(PyExc_RuntimeError, "Kein aktives iPad-Fenster für die Ausgabe.");
        return nullptr;
    }
    NSURL *url = [NSURL fileURLWithPath:resolved];
    dispatch_async(dispatch_get_main_queue(), ^{
        UIActivityViewController *share = [[UIActivityViewController alloc] initWithActivityItems:@[url] applicationActivities:nil];
        share.popoverPresentationController.sourceView = controller.view;
        share.popoverPresentationController.sourceRect = CGRectMake(CGRectGetMidX(controller.view.bounds), CGRectGetMaxY(controller.view.bounds)-60, 1, 1);
        share.completionWithItemsHandler = ^(UIActivityType, BOOL, NSArray *, NSError *) {
            [[NSFileManager defaultManager] removeItemAtURL:url error:nil];
            [[NSFileManager defaultManager] removeItemAtPath:resolved.stringByDeletingLastPathComponent error:nil];
        };
        [controller presentViewController:share animated:YES completion:nil];
    });
    Py_RETURN_NONE;
}
static PyObject *jkm_is_simulator(PyObject *, PyObject *)
{
    return PyBool_FromLong(TARGET_OS_SIMULATOR);
}
static PyMethodDef jkmMethods[] = {{"is_simulator", jkm_is_simulator, METH_NOARGS, "Report the compiled Apple simulator target."}, {"install_test_accessibility_mode", jkm_install_test_accessibility_mode, METH_NOARGS, "Temporarily omit Qt accessibility in the isolated test build."}, {"share_file", jkm_share_file, METH_VARARGS, "Open the native iPad PDF share sheet."}, {nullptr, nullptr, 0, nullptr}};
static PyModuleDef jkmModule = {PyModuleDef_HEAD_INIT, "jkm_ios_share", nullptr, -1, jkmMethods};
PyMODINIT_FUNC PyInit_jkm_ios_share(void) { return PyModule_Create(&jkmModule); }
