//! High-Precision Frame Pacer & Uncapped Rate Controller
//! ========================================================
//! Supports:
//! - Uncapped Mode: Maximum possible hardware throughput (supports 720Hz+ monitors and beyond).
//! - Target Cap Mode: User/Developer specified cap (e.g., 60, 144, 240, 360, 720 FPS).
//! - Sub-microsecond hybrid spin-wait to avoid Windows thread scheduler sleep jitter.

use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FrameLimit {
    Uncapped,
    Target(u32),
}

pub struct FramePacer {
    limit: FrameLimit,
    target_frame_duration: Option<Duration>,
    last_frame_time: Instant,
    frame_count: u64,
    fps_sample_start: Instant,
    current_fps: f64,
    frame_time_micros: f64,
}

impl FramePacer {
    pub fn new(limit: FrameLimit) -> Self {
        let now = Instant::now();
        let target_duration = match limit {
            FrameLimit::Uncapped => None,
            FrameLimit::Target(fps) => {
                if fps > 0 {
                    Some(Duration::from_nanos((1_000_000_000.0 / fps as f64) as u64))
                } else {
                    None
                }
            }
        };

        Self {
            limit,
            target_frame_duration: target_duration,
            last_frame_time: now,
            frame_count: 0,
            fps_sample_start: now,
            current_fps: 0.0,
            frame_time_micros: 0.0,
        }
    }

    /// Sets a new target FPS limit or sets to Uncapped.
    pub fn set_limit(&mut self, limit: FrameLimit) {
        self.limit = limit;
        self.target_frame_duration = match limit {
            FrameLimit::Uncapped => None,
            FrameLimit::Target(fps) => {
                if fps > 0 {
                    Some(Duration::from_nanos((1_000_000_000.0 / fps as f64) as u64))
                } else {
                    None
                }
            }
        };
    }

    /// Call at the beginning of each frame.
    /// Blocks with sub-microsecond hybrid spin-wait if running faster than target FPS.
    /// In Uncapped mode, it returns immediately without blocking.
    pub fn begin_frame(&mut self) -> Duration {
        if let Some(target_dur) = self.target_frame_duration {
            let elapsed = self.last_frame_time.elapsed();
            if elapsed < target_dur {
                let remaining = target_dur - elapsed;

                // Hybrid sleep + spin-wait:
                // If more than 2ms remaining, sleep to yield OS CPU:
                if remaining > Duration::from_millis(2) {
                    std::thread::sleep(remaining - Duration::from_millis(1));
                }

                // Tight spin-wait for final microsecond precision (zero jitter):
                while self.last_frame_time.elapsed() < target_dur {
                    std::hint::spin_loop();
                }
            }
        }

        let now = Instant::now();
        let delta = now.duration_since(self.last_frame_time);
        self.last_frame_time = now;
        self.frame_time_micros = delta.as_micros() as f64;

        // Update FPS counter every 250ms
        self.frame_count += 1;
        let sample_elapsed = now.duration_since(self.fps_sample_start);
        if sample_elapsed >= Duration::from_millis(250) {
            self.current_fps = (self.frame_count as f64 * 1000.0) / sample_elapsed.as_millis() as f64;
            self.frame_count = 0;
            self.fps_sample_start = now;
        }

        delta
    }

    pub fn current_fps(&self) -> f64 {
        self.current_fps
    }

    pub fn frame_time_micros(&self) -> f64 {
        self.frame_time_micros
    }

    pub fn limit(&self) -> FrameLimit {
        self.limit
    }
}
