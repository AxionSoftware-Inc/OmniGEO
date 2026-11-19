pub mod frame_pacer;
pub mod brep;
pub mod ray_brep;
pub mod assembly_bvh;
pub mod binary_format;
pub mod step_parser;

pub use frame_pacer::{FrameLimit, FramePacer};
pub use brep::{BoundingBox3D, BrepFace, SurfaceGeometry, Vec3};
pub use ray_brep::{AnalyticIntersector, Ray3D, RayHit};
pub use assembly_bvh::{AssemblyBvh, BvhNode};
pub use binary_format::{OmniCadArchive, PackedPart, SpatialPage};
pub use step_parser::{StepModel, StepParser, StepStats};

use std::ffi::{CStr, c_char};

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

// -------------------------------------------------------------------------
// STEP File Ingestion FFI
// -------------------------------------------------------------------------

#[unsafe(no_mangle)]
pub extern "C" fn omni_step_parse(filepath: *const c_char) -> *mut StepModel {
    if filepath.is_null() {
        return std::ptr::null_mut();
    }
    let c_str = unsafe { CStr::from_ptr(filepath) };
    let path_str = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    match StepParser::parse_file(path_str) {
        Ok(model) => Box::into_raw(Box::new(model)),
        Err(err) => {
            eprintln!("[Rust Core STEP] Parse error: {}", err);
            std::ptr::null_mut()
        }
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_step_get_part_count(model: *const StepModel) -> u32 {
    if model.is_null() {
        return 0;
    }
    let model = unsafe { &*model };
    model.canonical_parts.len() as u32
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_step_get_stats(model: *const StepModel, out_stats: *mut u32) {
    if model.is_null() || out_stats.is_null() {
        return;
    }
    let model = unsafe { &*model };
    unsafe {
        *out_stats.offset(0) = model.stats.cylinders as u32;
        *out_stats.offset(1) = model.stats.cones as u32;
        *out_stats.offset(2) = model.stats.spheres as u32;
        *out_stats.offset(3) = model.stats.torii as u32;
        *out_stats.offset(4) = model.stats.planes as u32;
        *out_stats.offset(5) = model.stats.nurbs_surfaces as u32;
        *out_stats.offset(6) = model.stats.solids as u32;
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_step_export_omnicad(
    model: *const StepModel,
    out_filepath: *const c_char,
) -> i32 {
    if model.is_null() || out_filepath.is_null() {
        return -1;
    }
    let model = unsafe { &*model };
    let c_str = unsafe { CStr::from_ptr(out_filepath) };
    let path_str = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return -2,
    };

    match model.export_to_omnicad(path_str) {
        Ok(bytes) => bytes as i32,
        Err(_) => -3,
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn omni_step_free(model: *mut StepModel) {
    if !model.is_null() {
        unsafe {
            drop(Box::from_raw(model));
        }
    }
}
