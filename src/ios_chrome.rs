//! The iPad's home indicator, the white bar at the bottom edge. A web view cannot ask for it to
//! hide and Tauri does not expose the view controller's preference, so this answers
//! `prefersHomeIndicatorAutoHidden` for the window's root view controller itself. iPadOS then
//! fades the bar after a few idle seconds; a swipe up from the edge still goes home.
//!
//! Only compiled for iOS (see ios-immersive.py).

use std::sync::atomic::{AtomicBool, Ordering};

use objc2::runtime::{AnyClass, AnyObject, Bool, Sel};
use objc2::{class, ffi, msg_send, sel};
use tauri::AppHandle;

/// What the controller answers. Written on the main thread, read by UIKit on the main thread.
static HIDE: AtomicBool = AtomicBool::new(false);
/// Whether the controller's class already answers from `HIDE`.
static ANSWERING: AtomicBool = AtomicBool::new(false);

extern "C-unwind" fn prefers_home_indicator_auto_hidden(
    _controller: *mut AnyObject,
    _selector: Sel,
) -> Bool {
    if HIDE.load(Ordering::Relaxed) {
        Bool::YES
    } else {
        Bool::NO
    }
}

/// The window's root view controller, or null before there is one. Main thread only.
fn root_view_controller() -> *mut AnyObject {
    // SAFETY: UIKit calls on the main thread. A message to nil returns nil, so a missing
    // application or window falls through to a null result.
    unsafe {
        let application: *mut AnyObject = msg_send![class!(UIApplication), sharedApplication];
        let mut window: *mut AnyObject = msg_send![application, keyWindow];
        if window.is_null() {
            let windows: *mut AnyObject = msg_send![application, windows];
            window = msg_send![windows, firstObject];
        }
        msg_send![window, rootViewController]
    }
}

/// Makes the controller's class answer `prefersHomeIndicatorAutoHidden` from `HIDE`.
fn answer_from_hide(controller: &AnyObject) {
    if ANSWERING.swap(true, Ordering::AcqRel) {
        return;
    }
    // SAFETY: replaces one method on the class of an object that exists. The new method has the
    // `BOOL (id, SEL)` shape UIKit calls it with, and it only reads an atomic.
    unsafe {
        let _ = ffi::class_replaceMethod(
            std::ptr::from_ref::<AnyClass>(controller.class()).cast_mut(),
            sel!(prefersHomeIndicatorAutoHidden),
            std::mem::transmute::<
                extern "C-unwind" fn(*mut AnyObject, Sel) -> Bool,
                objc2::runtime::Imp,
            >(prefers_home_indicator_auto_hidden),
            c"B@:".as_ptr(),
        );
    }
}

fn apply(hide: bool) {
    HIDE.store(hide, Ordering::Relaxed);
    // SAFETY: the pointer comes from UIKit on the main thread and is used only inside this call.
    let Some(controller) = (unsafe { root_view_controller().as_ref() }) else {
        tracing::warn!("No root view controller to hide the home indicator on");
        return;
    };
    answer_from_hide(controller);
    // SAFETY: a plain notification that the preference changed.
    unsafe {
        let _: () = msg_send![controller, setNeedsUpdateOfHomeIndicatorAutoHidden];
    }
}

/// Fades the home indicator out while `on` (fullscreen video) and brings it back when off.
#[tauri::command]
pub fn set_immersive(app: AppHandle, on: bool) {
    let _ = app.run_on_main_thread(move || apply(on));
}
