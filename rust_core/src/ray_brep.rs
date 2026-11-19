//! Direct Analytic B-Rep Ray-Intersection Engine
//! ===================================================
//! Intersects rays directly against exact CAD mathematical surfaces
//! WITHOUT any polygon discretization (Zero triangles, 100% exact curvature).

use crate::brep::{BoundingBox3D, BrepFace, SurfaceGeometry, Vec3};

#[derive(Debug, Clone, Copy)]
pub struct Ray3D {
    pub origin: Vec3,
    pub dir: Vec3,       // Normalized direction
    pub inv_dir: Vec3,   // 1.0 / dir for branchless slab intersection
}

impl Ray3D {
    pub fn new(origin: Vec3, dir: Vec3) -> Self {
        let dir = dir.normalize();
        let inv_dir = Vec3::new(
            if dir.x.abs() > 1e-14 { 1.0 / dir.x } else { 1e14 },
            if dir.y.abs() > 1e-14 { 1.0 / dir.y } else { 1e14 },
            if dir.z.abs() > 1e-14 { 1.0 / dir.z } else { 1e14 },
        );
        Self { origin, dir, inv_dir }
    }

    #[inline]
    pub fn point_at(&self, t: f64) -> Vec3 {
        self.origin + self.dir * t
    }
}

#[derive(Debug, Clone, Copy)]
pub struct RayHit {
    pub t: f64,
    pub point: Vec3,
    pub normal: Vec3,
    pub u: f64,
    pub v: f64,
    pub face_id: u64,
}

pub struct AnalyticIntersector;

impl AnalyticIntersector {
    /// Branchless AABB slab test (Kay & Kajiya / Smits)
    pub fn intersect_aabb(ray: &Ray3D, aabb: &BoundingBox3D, t_min: f64, t_max: f64) -> Option<(f64, f64)> {
        let t1 = (aabb.min.x - ray.origin.x) * ray.inv_dir.x;
        let t2 = (aabb.max.x - ray.origin.x) * ray.inv_dir.x;
        let t3 = (aabb.min.y - ray.origin.y) * ray.inv_dir.y;
        let t4 = (aabb.max.y - ray.origin.y) * ray.inv_dir.y;
        let t5 = (aabb.min.z - ray.origin.z) * ray.inv_dir.z;
        let t6 = (aabb.max.z - ray.origin.z) * ray.inv_dir.z;

        let t_enter = t1.min(t2).max(t3.min(t4)).max(t5.min(t6));
        let t_exit = t1.max(t2).min(t3.max(t4)).min(t5.max(t6));

        if t_exit < 0.0 || t_enter > t_exit || t_enter > t_max || t_exit < t_min {
            None
        } else {
            Some((t_enter, t_exit))
        }
    }

    /// Exact Analytic Sphere Intersection
    pub fn intersect_sphere(ray: &Ray3D, center: Vec3, radius: f64, t_min: f64, t_max: f64) -> Option<RayHit> {
        let oc = ray.origin - center;
        let b = oc.dot(ray.dir);
        let c = oc.dot(oc) - radius * radius;
        let discriminant = b * b - c;

        if discriminant < 0.0 {
            return None;
        }

        let sqrt_d = discriminant.sqrt();
        let mut t = -b - sqrt_d;

        if t < t_min || t > t_max {
            t = -b + sqrt_d;
            if t < t_min || t > t_max {
                return None;
            }
        }

        let point = ray.point_at(t);
        let normal = (point - center) * (1.0 / radius);

        // Spherical UV coordinates
        let u = 0.5 + normal.z.atan2(normal.x) / std::f64::consts::TAU;
        let v = 0.5 - normal.y.asin() / std::f64::consts::PI;

        Some(RayHit {
            t,
            point,
            normal,
            u,
            v,
            face_id: 0,
        })
    }

    /// Exact Analytic Cylinder Intersection (Capped between 0 and height along axis)
    pub fn intersect_cylinder(
        ray: &Ray3D,
        base: Vec3,
        axis: Vec3,
        radius: f64,
        height: f64,
        t_min: f64,
        t_max: f64,
    ) -> Option<RayHit> {
        let ro = ray.origin - base;
        let rd = ray.dir;

        // Project ray onto plane orthogonal to cylinder axis
        let d_axis = axis * rd.dot(axis);
        let d_ortho = rd - d_axis;

        let ro_axis = axis * ro.dot(axis);
        let ro_ortho = ro - ro_axis;

        let a = d_ortho.dot(d_ortho);
        let b = 2.0 * ro_ortho.dot(d_ortho);
        let c = ro_ortho.dot(ro_ortho) - radius * radius;

        if a.abs() < 1e-14 {
            return None; // Ray is parallel to axis
        }

        let discriminant = b * b - 4.0 * a * c;
        if discriminant < 0.0 {
            return None;
        }

        let sqrt_d = discriminant.sqrt();
        let t1 = (-b - sqrt_d) / (2.0 * a);
        let t2 = (-b + sqrt_d) / (2.0 * a);

        let mut closest_hit: Option<RayHit> = None;

        for &t in &[t1, t2] {
            if t >= t_min && t <= t_max {
                let p = ray.point_at(t);
                let h = (p - base).dot(axis);

                if h >= 0.0 && h <= height {
                    let normal = ((p - base) - axis * h) * (1.0 / radius);
                    let angle = normal.z.atan2(normal.x);
                    let u = (angle + std::f64::consts::PI) / std::f64::consts::TAU;
                    let v = h / height;

                    if closest_hit.is_none() || t < closest_hit.as_ref().unwrap().t {
                        closest_hit = Some(RayHit {
                            t,
                            point: p,
                            normal,
                            u,
                            v,
                            face_id: 0,
                        });
                    }
                }
            }
        }

        closest_hit
    }

    /// Intersects any exact B-Rep Face directly
    pub fn intersect_face(ray: &Ray3D, face: &BrepFace, t_min: f64, t_max: f64) -> Option<RayHit> {
        // Fast AABB rejection
        let aabb = face.compute_bounding_box();
        if Self::intersect_aabb(ray, &aabb, t_min, t_max).is_none() {
            return None;
        }

        let mut hit = match &face.surface {
            SurfaceGeometry::Sphere { center, radius } => {
                Self::intersect_sphere(ray, *center, *radius, t_min, t_max)
            }
            SurfaceGeometry::Cylinder { base, axis, radius, height } => {
                Self::intersect_cylinder(ray, *base, *axis, *radius, *height, t_min, t_max)
            }
            SurfaceGeometry::Plane { origin, normal, u_axis, v_axis } => {
                let denom = normal.dot(ray.dir);
                if denom.abs() > 1e-12 {
                    let t = (origin.clone() - ray.origin).dot(*normal) / denom;
                    if t >= t_min && t <= t_max {
                        let pt = ray.point_at(t);
                        let diff = pt - *origin;
                        let u = diff.dot(*u_axis);
                        let v = diff.dot(*v_axis);
                        Some(RayHit {
                            t,
                            point: pt,
                            normal: *normal,
                            u,
                            v,
                            face_id: face.id,
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            }
            _ => None,
        };

        if let Some(ref mut h) = hit {
            h.face_id = face.id;
        }

        hit
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_analytic_sphere_hit() {
        let ray = Ray3D::new(Vec3::new(0.0, 0.0, -10.0), Vec3::new(0.0, 0.0, 1.0));
        let hit = AnalyticIntersector::intersect_sphere(&ray, Vec3::ZERO, 2.0, 0.1, 100.0);

        assert!(hit.is_some());
        let h = hit.unwrap();
        assert!((h.t - 8.0).abs() < 1e-12); // Ray origin is at -10, radius 2 => hit at z = -2, t = 8
        assert!((h.point.z - (-2.0)).abs() < 1e-12);
        assert!((h.normal.z - (-1.0)).abs() < 1e-12);
    }

    #[test]
    fn test_analytic_cylinder_hit() {
        let ray = Ray3D::new(Vec3::new(-10.0, 5.0, 0.0), Vec3::new(1.0, 0.0, 0.0));
        let hit = AnalyticIntersector::intersect_cylinder(
            &ray,
            Vec3::ZERO,
            Vec3::Y,
            3.0,
            10.0,
            0.1,
            100.0,
        );

        assert!(hit.is_some());
        let h = hit.unwrap();
        assert!((h.t - 7.0).abs() < 1e-12); // Hits at x = -3, t = 7
        assert_eq!(h.point.y, 5.0);
        assert!((h.normal.x - (-1.0)).abs() < 1e-12);
    }
}
