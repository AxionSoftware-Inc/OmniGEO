pub mod frame_pacer;

pub use frame_pacer::{FrameLimit, FramePacer};

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_720hz_pacer() {
        let mut pacer = FramePacer::new(FrameLimit::Target(720));
        let expected_micros = 1_000_000.0 / 720.0; // ~1388.89 us

        for _ in 0..60 {
            let _delta = pacer.begin_frame();
            let mut sum: u64 = 0;
            for i in 0..1000 {
                sum = sum.wrapping_add(i);
            }
            std::hint::black_box(sum);
        }

        println!("720 FPS Target: {:.2} us | Achieved: {:.2} us",
            expected_micros, pacer.frame_time_micros());
        assert!((pacer.frame_time_micros() - expected_micros).abs() < 250.0);
    }

    #[test]
    fn test_uncapped_throughput() {
        let mut pacer = FramePacer::new(FrameLimit::Uncapped);
        let start = std::time::Instant::now();
        let frames = 100_000;

        for _ in 0..frames {
            let _ = pacer.begin_frame();
        }

        let total_time = start.elapsed();
        let fps = frames as f64 / total_time.as_secs_f64();
        println!("Uncapped frame loop throughput: {:.0} FPS!", fps);
        assert!(fps > 100_000.0);
    }
}
