pub mod frame_pacer;
pub mod brep;
pub mod ray_brep;
pub mod assembly_bvh;

pub use frame_pacer::{FrameLimit, FramePacer};
pub use brep::{BoundingBox3D, BrepFace, SurfaceGeometry, Vec3};
pub use ray_brep::{AnalyticIntersector, Ray3D, RayHit};
pub use assembly_bvh::{AssemblyBvh, BvhNode};

// =========================================================================
// C ABI / FFI Export for Python, C++, and Host Bindings
// =========================================================================

#[unsafe(no_mangle)]
pub extern "C" fn omni_pacer_create(target_fps: u32) -> *mut FramePacer {
    let limit = if target_fps == 0 {
        FrameLimit::Uncapped
    } else {
        FrameLimit::Target(target_fps)
    };
    Box::into_raw(Box::new(FramePacer::new(limit)))
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_pacer_set_limit(pacer: *mut FramePacer, target_fps: u32) {
    if pacer.is_null() {
        return;
    }
    let pacer = unsafe { &mut *pacer };
    let limit = if target_fps == 0 {
        FrameLimit::Uncapped
    } else {
        FrameLimit::Target(target_fps)
    };
    pacer.set_limit(limit);
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_pacer_begin_frame(pacer: *mut FramePacer) -> f64 {
    if pacer.is_null() {
        return 0.0;
    }
    let pacer = unsafe { &mut *pacer };
    let _ = pacer.begin_frame();
    pacer.frame_time_micros()
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_pacer_get_fps(pacer: *mut FramePacer) -> f64 {
    if pacer.is_null() {
        return 0.0;
    }
    let pacer = unsafe { &*pacer };
    pacer.current_fps()
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_pacer_destroy(pacer: *mut FramePacer) {
    if !pacer.is_null() {
        unsafe {
            drop(Box::from_raw(pacer));
        }
    }
}
