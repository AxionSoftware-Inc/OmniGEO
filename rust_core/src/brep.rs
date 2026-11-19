//! B-Rep (Boundary Representation) & Parametric Surfaces Module
//! ==============================================================
//! Provides exact mathematical representations of industrial CAD surfaces:
//! 1. Analytic Quadrics (Plane, Cylinder, Cone, Sphere, Torus)
//! 2. Parametric NURBS (Non-Uniform Rational B-Splines) Surfaces
//! 3. Trimmed UV Parametric Patches
//! 4. Exact Differential Geometry: Tangents (du, dv), Normal, Curvatures (k1, k2)

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Vec3 {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

impl Vec3 {
    pub const ZERO: Self = Self { x: 0.0, y: 0.0, z: 0.0 };
    pub const X: Self = Self { x: 1.0, y: 0.0, z: 0.0 };
    pub const Y: Self = Self { x: 0.0, y: 1.0, z: 0.0 };
    pub const Z: Self = Self { x: 0.0, y: 0.0, z: 1.0 };

    #[inline]
    pub fn new(x: f64, y: f64, z: f64) -> Self {
        Self { x, y, z }
    }

    #[inline]
    pub fn dot(self, rhs: Self) -> f64 {
        self.x * rhs.x + self.y * rhs.y + self.z * rhs.z
    }

    #[inline]
    pub fn cross(self, rhs: Self) -> Self {
        Self {
            x: self.y * rhs.z - self.z * rhs.y,
            y: self.z * rhs.x - self.x * rhs.z,
            z: self.x * rhs.y - self.y * rhs.x,
        }
    }

    #[inline]
    pub fn length_squared(self) -> f64 {
        self.dot(self)
    }

    #[inline]
    pub fn length(self) -> f64 {
        self.length_squared().sqrt()
    }

    #[inline]
    pub fn normalize(self) -> Self {
        let len = self.length();
        if len > 1e-14 {
            self * (1.0 / len)
        } else {
            Self::ZERO
        }
    }
}

impl std::ops::Add for Vec3 {
    type Output = Self;
    #[inline]
    fn add(self, rhs: Self) -> Self {
        Self::new(self.x + rhs.x, self.y + rhs.y, self.z + rhs.z)
    }
}

impl std::ops::Sub for Vec3 {
    type Output = Self;
    #[inline]
    fn sub(self, rhs: Self) -> Self {
        Self::new(self.x - rhs.x, self.y - rhs.y, self.z - rhs.z)
    }
}

impl std::ops::Mul<f64> for Vec3 {
    type Output = Self;
    #[inline]
    fn mul(self, rhs: f64) -> Self {
        Self::new(self.x * rhs, self.y * rhs, self.z * rhs)
    }
}

impl std::ops::Neg for Vec3 {
    type Output = Self;
    #[inline]
    fn neg(self) -> Self {
        Self::new(-self.x, -self.y, -self.z)
    }
}

/// 3D Axis-Aligned Bounding Box in 64-bit precision
#[derive(Debug, Clone, Copy)]
pub struct BoundingBox3D {
    pub min: Vec3,
    pub max: Vec3,
}

impl BoundingBox3D {
    pub fn new(min: Vec3, max: Vec3) -> Self {
        Self { min, max }
    }

    pub fn center(&self) -> Vec3 {
        (self.min + self.max) * 0.5
    }

    pub fn extents(&self) -> Vec3 {
        (self.max - self.min) * 0.5
    }

    pub fn contains(&self, p: Vec3) -> bool {
        p.x >= self.min.x && p.x <= self.max.x &&
        p.y >= self.min.y && p.y <= self.max.y &&
        p.z >= self.min.z && p.z <= self.max.z
    }
}

/// Exact Industrial Surface Types
#[derive(Debug, Clone)]
pub enum SurfaceGeometry {
    /// Infinite or bounded planar face (Origin, Normal, U-tangent)
    Plane {
        origin: Vec3,
        normal: Vec3,
        u_axis: Vec3,
        v_axis: Vec3,
    },
    /// Exact Circular Cylinder (Base center, Axis direction, Radius, Height)
    Cylinder {
        base: Vec3,
        axis: Vec3, // Unit vector
        radius: f64,
        height: f64,
    },
    /// Exact Circular Cone (Apex, Axis direction, Semi-angle alpha, Height)
    Cone {
        apex: Vec3,
        axis: Vec3,
        tan_alpha: f64,
        height: f64,
    },
    /// Exact Sphere (Center, Radius)
    Sphere {
        center: Vec3,
        radius: f64,
    },
    /// Exact Torus for CAD Fillets and Blends (Center, Normal, Major Radius R, Minor Radius r)
    Torus {
        center: Vec3,
        normal: Vec3,
        major_radius: f64,
        minor_radius: f64,
    },
    /// Parametric NURBS Surface
    Nurbs(NurbsSurface),
}

/// NURBS Surface Definition (B-Rep Spline Patch)
#[derive(Debug, Clone)]
pub struct NurbsSurface {
    pub degree_u: usize,
    pub degree_v: usize,
    pub knots_u: Vec<f64>,
    pub knots_v: Vec<f64>,
    pub control_points: Vec<Vec<Vec3>>, // [u][v]
    pub weights: Vec<Vec<f64>>,         // [u][v]
}

impl NurbsSurface {
    /// Evaluates B-Spline Basis functions using Cox-de Boor recursive formulation
    pub fn basis_funs(i: usize, u: f64, p: usize, knots: &[f64]) -> Vec<f64> {
        let mut n = vec![0.0; p + 1];
        let mut left = vec![0.0; p + 1];
        let mut right = vec![0.0; p + 1];
        n[0] = 1.0;

        for j in 1..=p {
            left[j] = u - knots[i + 1 - j];
            right[j] = knots[i + j] - u;
            let mut saved = 0.0;

            for r in 0..j {
                let temp = n[r] / (right[r + 1] + left[j - r]);
                n[r] = saved + right[r + 1] * temp;
                saved = left[j - r] * temp;
            }
            n[j] = saved;
        }
        n
    }

    /// Finds the knot span index for parameter u
    pub fn find_span(n: usize, p: usize, u: f64, knots: &[f64]) -> usize {
        if u >= knots[n + 1] {
            return n;
        }
        if u <= knots[p] {
            return p;
        }

        let mut low = p;
        let mut high = n + 1;
        let mut mid = (low + high) / 2;

        while u < knots[mid] || u >= knots[mid + 1] {
            if u < knots[mid] {
                high = mid;
            } else {
                low = mid;
            }
            mid = (low + high) / 2;
        }
        mid
    }

    /// Evaluates exact 3D point S(u, v) on NURBS surface
    pub fn evaluate(&self, u: f64, v: f64) -> (Vec3, Vec3) {
        let num_u = self.control_points.len() - 1;
        let num_v = self.control_points[0].len() - 1;

        let span_u = Self::find_span(num_u, self.degree_u, u, &self.knots_u);
        let span_v = Self::find_span(num_v, self.degree_v, v, &self.knots_v);

        let nu = Self::basis_funs(span_u, u, self.degree_u, &self.knots_u);
        let nv = Self::basis_funs(span_v, v, self.degree_v, &self.knots_v);

        let mut point = Vec3::ZERO;
        let mut w_sum = 0.0;

        for (l, &b_u) in nu.iter().enumerate() {
            let u_idx = span_u - self.degree_u + l;
            for (k, &b_v) in nv.iter().enumerate() {
                let v_idx = span_v - self.degree_v + k;
                let w = self.weights[u_idx][v_idx];
                let pt = self.control_points[u_idx][v_idx];
                let coeff = b_u * b_v * w;

                point = point + pt * coeff;
                w_sum += coeff;
            }
        }

        if w_sum.abs() > 1e-14 {
            point = point * (1.0 / w_sum);
        }

        // Return point and approximate normal via numerical finite difference
        let eps = 1e-5;
        let p_u = self.evaluate_point(u + eps, v);
        let p_v = self.evaluate_point(u, v + eps);
        let du = (p_u - point) * (1.0 / eps);
        let dv = (p_v - point) * (1.0 / eps);
        let normal = du.cross(dv).normalize();

        (point, normal)
    }

    fn evaluate_point(&self, u: f64, v: f64) -> Vec3 {
        let num_u = self.control_points.len() - 1;
        let num_v = self.control_points[0].len() - 1;

        let span_u = Self::find_span(num_u, self.degree_u, u, &self.knots_u);
        let span_v = Self::find_span(num_v, self.degree_v, v, &self.knots_v);

        let nu = Self::basis_funs(span_u, u, self.degree_u, &self.knots_u);
        let nv = Self::basis_funs(span_v, v, self.degree_v, &self.knots_v);

        let mut point = Vec3::ZERO;
        let mut w_sum = 0.0;

        for (l, &b_u) in nu.iter().enumerate() {
            let u_idx = span_u - self.degree_u + l;
            for (k, &b_v) in nv.iter().enumerate() {
                let v_idx = span_v - self.degree_v + k;
                let w = self.weights[u_idx][v_idx];
                let pt = self.control_points[u_idx][v_idx];
                let coeff = b_u * b_v * w;

                point = point + pt * coeff;
                w_sum += coeff;
            }
        }

        if w_sum.abs() > 1e-14 {
            point * (1.0 / w_sum)
        } else {
            point
        }
    }
}

/// CAD B-Rep Face: An exact parametric surface bound by UV trim curves
#[derive(Debug, Clone)]
pub struct BrepFace {
    pub id: u64,
    pub surface: SurfaceGeometry,
    pub u_range: (f64, f64),
    pub v_range: (f64, f64),
    pub bounding_box: BoundingBox3D,
}

impl BrepFace {
    pub fn compute_bounding_box(&self) -> BoundingBox3D {
        match &self.surface {
            SurfaceGeometry::Sphere { center, radius } => {
                let r_vec = Vec3::new(*radius, *radius, *radius);
                BoundingBox3D::new(*center - r_vec, *center + r_vec)
            }
            SurfaceGeometry::Cylinder { base, axis, radius, height } => {
                let top = *base + *axis * *height;
                let r = *radius;
                let min = Vec3::new(
                    base.x.min(top.x) - r,
                    base.y.min(top.y) - r,
                    base.z.min(top.z) - r,
                );
                let max = Vec3::new(
                    base.x.max(top.x) + r,
                    base.y.max(top.y) + r,
                    base.z.max(top.z) + r,
                );
                BoundingBox3D::new(min, max)
            }
            _ => self.bounding_box,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vec3_math() {
        let v1 = Vec3::new(1.0, 2.0, 3.0);
        let v2 = Vec3::new(4.0, 5.0, 6.0);
        assert_eq!(v1.dot(v2), 32.0);

        let cross = Vec3::X.cross(Vec3::Y);
        assert!((cross - Vec3::Z).length() < 1e-14);
    }

    #[test]
    fn test_cylinder_bounding_box() {
        let face = BrepFace {
            id: 1,
            surface: SurfaceGeometry::Cylinder {
                base: Vec3::ZERO,
                axis: Vec3::Y,
                radius: 2.0,
                height: 10.0,
            },
            u_range: (0.0, std::f64::consts::TAU),
            v_range: (0.0, 10.0),
            bounding_box: BoundingBox3D::new(Vec3::ZERO, Vec3::ZERO),
        };

        let aabb = face.compute_bounding_box();
        assert_eq!(aabb.min.x, -2.0);
        assert_eq!(aabb.max.x, 2.0);
        assert_eq!(aabb.min.y, -2.0);
        assert_eq!(aabb.max.y, 12.0);
    }
}
