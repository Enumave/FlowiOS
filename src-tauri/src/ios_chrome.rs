//! The iPad's home indicator, the white bar at the bottom edge. A web view cannot ask for it to
//! hide and Tauri does not expose the view controller's preference, so this answers
//! `prefersHomeIndicatorAutoHidden` for the window's root view controller itself. iPadOS then
//! fades the bar after a few idle seconds; a swipe up from the edge still goes home.
//!
//! The status bar leaves with it (see `set_status_bar_hidden`).
//!
//! Also here: the screen brightness and system volume the fullscreen swipe gestures move, as on
//! Android (left side brightness, right side volume). A web view can set neither: iOS ignores
//! `HTMLMediaElement.volume`, and there is no brightness API. Brightness is `UIScreen`'s and is put
//! back when fullscreen ends. Volume goes through the slider inside an `MPVolumeView`, which is the
//! only public way to move the system volume; the view is in the window only while a swipe is
//! under way, because while it is there the system's own volume pop-up is suppressed.
//!
//! Only compiled for iOS, and only from src-tauri/src/ (see ios-immersive.py).

use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicU64, Ordering};
use std::time::Duration;

use objc2::rc::{Allocated, Retained};
use objc2::runtime::{AnyClass, AnyObject, Bool, Sel};
use objc2::{class, ffi, msg_send, sel};
use tauri::AppHandle;

/// What the controller answers. Written on the main thread, read by UIKit on the main thread.
static HIDE: AtomicBool = AtomicBool::new(false);
/// Whether the controller's class already answers from `HIDE`.
static ANSWERING: AtomicBool = AtomicBool::new(false);

// `MPVolumeView` lives in MediaPlayer, which nothing else here pulls in.
#[link(name = "MediaPlayer", kind = "framework")]
unsafe extern "C" {}

/// The brightness the screen had before a swipe changed it, as `f64` bits, if one did.
static SAVED_BRIGHTNESS: AtomicU64 = AtomicU64::new(0);
static HAS_SAVED_BRIGHTNESS: AtomicBool = AtomicBool::new(false);
/// The `MPVolumeView` that is in the window for the length of a swipe, or null.
static VOLUME_VIEW: AtomicPtr<AnyObject> = AtomicPtr::new(std::ptr::null_mut());

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
            std::ptr::from_ref::<AnyClass>(controller.class()).cast_mut().cast(),
            sel!(prefersHomeIndicatorAutoHidden),
            std::mem::transmute::<
                extern "C-unwind" fn(*mut AnyObject, Sel) -> Bool,
                objc2::runtime::Imp,
            >(prefers_home_indicator_auto_hidden),
            c"B@:".as_ptr(),
        );
    }
}
/// The status bar (time, date, battery) leaves with the home indicator. This is the
/// application-level call, which works because Info.ios.plist turns off view-controller-based
/// status bar appearance. 1 is UIStatusBarAnimationFade.
fn set_status_bar_hidden(hidden: bool) {
    // SAFETY: a UIKit call on the main thread; `apply` only runs there.
    unsafe {
        let application: *mut AnyObject = msg_send![class!(UIApplication), sharedApplication];
        let _: () = msg_send![application, setStatusBarHidden: Bool::new(hidden), withAnimation: 1isize];
    }
}

/// The main screen, or null.
fn main_screen() -> *mut AnyObject {
    // SAFETY: a UIKit call on the main thread (every caller runs there).
    unsafe { msg_send![class!(UIScreen), mainScreen] }
}

/// The screen brightness from 0 to 1, or -1 when there is no screen.
fn brightness() -> f64 {
    let screen = main_screen();
    if screen.is_null() {
        return -1.0;
    }
    // SAFETY: `screen` is a live UIScreen.
    unsafe { msg_send![screen, brightness] }
}

/// Writes the brightness without touching the saved original.
fn write_brightness(value: f64) {
    let screen = main_screen();
    if screen.is_null() {
        return;
    }
    // SAFETY: `screen` is a live UIScreen; brightness is clamped to the range it accepts.
    unsafe {
        let _: () = msg_send![screen, setBrightness: value.clamp(0.0, 1.0)];
    }
}

fn set_brightness(value: f64) {
    // Remember what the screen was set to before the first swipe, to put it back afterwards.
    if !HAS_SAVED_BRIGHTNESS.swap(true, Ordering::AcqRel) {
        SAVED_BRIGHTNESS.store(brightness().to_bits(), Ordering::Relaxed);
    }
    write_brightness(value);
}

/// Puts the brightness back to what it was before the first swipe, once fullscreen is over.
fn restore_brightness() {
    if HAS_SAVED_BRIGHTNESS.swap(false, Ordering::AcqRel) {
        let saved = f64::from_bits(SAVED_BRIGHTNESS.load(Ordering::Relaxed));
        if saved >= 0.0 {
            write_brightness(saved);
        }
    }
}

/// Adds a zero-size `MPVolumeView` to the window if there is not one already.
fn attach_volume_view() {
    if !VOLUME_VIEW.load(Ordering::Acquire).is_null() {
        return;
    }
    // SAFETY: UIKit calls on the main thread. `init` gives a zero frame, which is all this needs.
    // The view is kept alive by one reference that is turned into a raw pointer here and given
    // back in `detach_volume_view`.
    unsafe {
        let Some(controller) = root_view_controller().as_ref() else {
            return;
        };
        let allocated: Allocated<AnyObject> = msg_send![class!(MPVolumeView), alloc];
        let created: Option<Retained<AnyObject>> = msg_send![allocated, init];
        let Some(view) = created else {
            return;
        };
        let view = Retained::into_raw(view);
        // A zero-size view still lets its slider's thumb draw at the corner (a white dot), so it is
        // clipped to its empty bounds and made all but transparent. It must stay in the window and
        // not be hidden, or iOS shows its own volume pop-up over ours.
        let _: () = msg_send![view, setClipsToBounds: Bool::YES];
        let _: () = msg_send![view, setAlpha: 0.01_f64];
        let parent: *mut AnyObject = msg_send![controller, view];
        let _: () = msg_send![parent, addSubview: view];
        let _: () = msg_send![view, layoutIfNeeded];
        VOLUME_VIEW.store(view, Ordering::Release);
    }
}

fn detach_volume_view() {
    let view = VOLUME_VIEW.swap(std::ptr::null_mut(), Ordering::AcqRel);
    if view.is_null() {
        return;
    }
    // SAFETY: `view` is the pointer `attach_volume_view` made from its own reference, so taking
    // that reference back and dropping it after the view leaves the window balances it.
    unsafe {
        let _: () = msg_send![view, removeFromSuperview];
        drop(Retained::from_raw(view));
    }
}

/// The slider inside the volume view, or null before it has appeared.
fn volume_slider() -> *mut AnyObject {
    let view = VOLUME_VIEW.load(Ordering::Acquire);
    if view.is_null() {
        return std::ptr::null_mut();
    }
    // SAFETY: `view` is live while it is stored; `subviews` is an NSArray of views.
    unsafe {
        let subviews: *mut AnyObject = msg_send![view, subviews];
        let count: usize = msg_send![subviews, count];
        for index in 0..count {
            let subview: *mut AnyObject = msg_send![subviews, objectAtIndex: index];
            let is_slider: Bool = msg_send![subview, isKindOfClass: class!(UISlider)];
            if is_slider.as_bool() {
                return subview;
            }
        }
    }
    std::ptr::null_mut()
}

/// The system volume from 0 to 1, or -1 while the slider is not there yet.
fn system_volume() -> f64 {
    let slider = volume_slider();
    if slider.is_null() {
        return -1.0;
    }
    // SAFETY: `slider` is a live UISlider.
    let value: f32 = unsafe { msg_send![slider, value] };
    f64::from(value)
}

fn set_system_volume_level(value: f64) {
    let slider = volume_slider();
    if slider.is_null() {
        return;
    }
    // SAFETY: `slider` is a live UISlider; the value is clamped to its range.
    unsafe {
        let _: () = msg_send![slider, setValue: value.clamp(0.0, 1.0) as f32];
    }
}

fn apply(hide: bool) {
    HIDE.store(hide, Ordering::Relaxed);
    set_status_bar_hidden(hide);
    if !hide {
        // Fullscreen is over: the swipes' brightness change was only for the video.
        restore_brightness();
        detach_volume_view();
    }
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

/// Starts a brightness or volume swipe and returns the current `(brightness, volume)`, each 0 to 1.
/// The volume view is in the window only for a volume swipe (`with_volume`), so a brightness swipe
/// never touches the system volume pop-up. Volume is -1 when there is no slider yet, which the
/// caller retries. Async so that it can wait for the main thread without being on it.
#[tauri::command]
pub async fn begin_screen_levels(app: AppHandle, with_volume: bool) -> Result<(f64, f64), String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        if with_volume {
            attach_volume_view();
        } else {
            detach_volume_view();
        }
        let _ = sender.send((brightness(), system_volume()));
    })
    .map_err(|error| error.to_string())?;
    receiver
        .recv_timeout(Duration::from_millis(500))
        .map_err(|error| error.to_string())
}

/// Ends the swipe: the volume view leaves the window, so the system volume pop-up works again.
#[tauri::command]
pub fn end_screen_levels(app: AppHandle) {
    let _ = app.run_on_main_thread(detach_volume_view);
}

#[tauri::command]
pub fn set_screen_brightness(app: AppHandle, value: f64) {
    let _ = app.run_on_main_thread(move || set_brightness(value));
}

#[tauri::command]
pub fn set_system_volume(app: AppHandle, value: f64) {
    let _ = app.run_on_main_thread(move || set_system_volume_level(value));
}
