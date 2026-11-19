//! STEP (ISO 10303-21) CAD Assembly Ingestion & Parser
//! =========================================================
//! Parses real industrial STEP files (AP203, AP214, AP242).
//! Extracts canonical quadrics (Cylinders, Cones, Spheres, Torii, Planes)
//! and Freeform NURBS surfaces, converting them directly into OmniGEO's
//! ultra-compact 32-byte `PackedPart` format and B-Rep structures.

use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;

use crate::brep::{BoundingBox3D, NurbsSurface, Vec3};
use crate::binary_format::{OmniCadArchive, PackedPart};

/// Raw parameter value parsed from STEP entity argument list
#[derive(Debug, Clone, PartialEq)]
pub enum StepValue {
    EntityRef(u64),
    Number(f64),
    Text(String),
    Enumeration(String),
    List(Vec<StepValue>),
}

impl StepValue {
    pub fn as_u64(&self) -> Option<u64> {
        match self {
            StepValue::EntityRef(id) => Some(*id),
            StepValue::Number(n) => Some(*n as u64),
            _ => None,
        }
    }

    pub fn as_f64(&self) -> Option<f64> {
        match self {
            StepValue::Number(n) => Some(*n),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&[StepValue]> {
        match self {
            StepValue::List(l) => Some(l.as_slice()),
            _ => None,
        }
    }

    pub fn as_vec3(&self) -> Option<Vec3> {
        if let StepValue::List(l) = self {
            if l.len() >= 3 {
                let x = l[0].as_f64()?;
                let y = l[1].as_f64()?;
                let z = l[2].as_f64()?;
                return Some(Vec3::new(x, y, z));
            }
        }
        None
    }
}

/// Raw parsed STEP entity
#[derive(Debug, Clone)]
pub struct RawEntity {
    pub id: u64,
    pub entity_type: String,
    pub params: Vec<StepValue>,
}

/// Axis2Placement3D represents the local coordinate system of a CAD part or surface
#[derive(Debug, Clone, Copy)]
pub struct Axis2Placement3D {
    pub location: Vec3,
    pub axis: Vec3,       // Z-axis (normal)
    pub ref_direction: Vec3, // X-axis
}

impl Axis2Placement3D {
    pub const IDENTITY: Self = Self {
        location: Vec3::ZERO,
        axis: Vec3::Z,
        ref_direction: Vec3::X,
    };
}

/// Result of importing a STEP model
#[derive(Debug, Default)]
pub struct StepModel {
    pub file_name: String,
    pub total_entities: usize,
    pub canonical_parts: Vec<PackedPart>,
    pub freeform_surfaces: Vec<NurbsSurface>,
    pub bounding_box: BoundingBox3D,
    pub stats: StepStats,
}

#[derive(Debug, Default, Clone, Copy)]
pub struct StepStats {
    pub cylinders: usize,
    pub cones: usize,
    pub spheres: usize,
    pub torii: usize,
    pub planes: usize,
    pub nurbs_surfaces: usize,
    pub solids: usize,
}

impl Default for BoundingBox3D {
    fn default() -> Self {
        Self {
            min: Vec3::new(f64::MAX, f64::MAX, f64::MAX),
            max: Vec3::new(f64::MIN, f64::MIN, f64::MIN),
        }
    }
}

pub struct StepParser {
    entities: HashMap<u64, RawEntity>,
}

impl StepParser {
    pub fn new() -> Self {
        Self {
            entities: HashMap::new(),
        }
    }

    /// Loads and parses a STEP file from disk
    pub fn parse_file<P: AsRef<Path>>(path: P) -> Result<StepModel, String> {
        let path_ref = path.as_ref();
        let file = File::open(path_ref).map_err(|e| format!("Fayl ochishda xatolik: {}", e))?;
        let reader = BufReader::new(file);

        let mut parser = Self::new();
        let file_name = path_ref
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown.stp")
            .to_string();

        let mut in_data = false;
        let mut buffer = String::with_capacity(2048);

        for line in reader.lines() {
            let line = line.map_err(|e| format!("Faylni o'qish xatosi: {}", e))?;
            let trimmed = line.trim();

            if trimmed.starts_with("DATA;") {
                in_data = true;
                continue;
            }
            if trimmed.starts_with("ENDSEC;") && in_data {
                break;
            }
            if !in_data {
                continue;
            }

            buffer.push_str(trimmed);
            if buffer.ends_with(';') {
                // Remove trailing ';'
                buffer.pop();
                parser.parse_statement(&buffer);
                buffer.clear();
            }
        }

        parser.build_model(file_name)
    }

    /// Parses a single statement like `#123 = CYLINDRICAL_SURFACE('', #45, 12.5)`
    fn parse_statement(&mut self, stmt: &str) {
        let mut stmt = stmt.trim();
        if let Some(stripped) = stmt.strip_suffix(';') {
            stmt = stripped.trim();
        }
        if !stmt.starts_with('#') {
            return;
        }

        let eq_idx = match stmt.find('=') {
            Some(i) => i,
            None => return,
        };

        let id_str = stmt[1..eq_idx].trim();
        let id: u64 = match id_str.parse() {
            Ok(v) => v,
            Err(_) => return,
        };

        let rhs = stmt[eq_idx + 1..].trim();
        if rhs.starts_with('(') {
            // Complex entity: e.g. ( BOUNDED_SURFACE() B_SPLINE_SURFACE(...) ... )
            self.parse_complex_entity(id, rhs);
        } else if let Some(paren_idx) = rhs.find('(') {
            let entity_type = rhs[..paren_idx].trim().to_uppercase();
            let args_str = &rhs[paren_idx..];
            let params = Self::parse_arg_list(args_str);
            self.entities.insert(
                id,
                RawEntity {
                    id,
                    entity_type,
                    params,
                },
            );
        }
    }

    /// Parses complex entities enclosed in parentheses
    fn parse_complex_entity(&mut self, id: u64, rhs: &str) {
        let chars: Vec<char> = rhs.chars().collect();
        let mut i = 0;
        if i < chars.len() && chars[i] == '(' {
            i += 1;
        }
        let mut sub_entities = Vec::new();

        while i < chars.len() {
            while i < chars.len() && (chars[i].is_whitespace() || chars[i] == ')') {
                i += 1;
            }
            if i >= chars.len() {
                break;
            }

            let start_i = i;
            let name_start = i;
            while i < chars.len() && chars[i] != '(' && !chars[i].is_whitespace() && chars[i] != ')' {
                i += 1;
            }
            let entity_name: String = chars[name_start..i].iter().collect();

            while i < chars.len() && chars[i].is_whitespace() {
                i += 1;
            }

            if i < chars.len() && chars[i] == '(' {
                let paren_start = i;
                let mut depth = 0;
                while i < chars.len() {
                    if chars[i] == '(' {
                        depth += 1;
                    } else if chars[i] == ')' {
                        depth -= 1;
                        if depth == 0 {
                            i += 1;
                            break;
                        }
                    }
                    i += 1;
                }
                let args_str: String = chars[paren_start..i].iter().collect();
                let params = Self::parse_arg_list(&args_str);
                sub_entities.push((entity_name, params));
            }

            if i == start_i {
                i += 1;
            }
        }

        // Prefer specific surface types (e.g. B_SPLINE_SURFACE) over generic BOUNDED_SURFACE
        let mut best_choice = None;
        for (ename, eparams) in sub_entities {
            let u_name = ename.to_uppercase();
            if u_name.contains("B_SPLINE_SURFACE")
                || u_name.contains("CYLINDRICAL")
                || u_name.contains("CONICAL")
                || u_name.contains("TOROIDAL")
            {
                best_choice = Some((u_name, eparams));
                break;
            } else if best_choice.is_none()
                && (u_name.contains("SURFACE") || u_name.contains("SOLID") || u_name.contains("CURVE"))
            {
                best_choice = Some((u_name, eparams));
            }
        }

        if let Some((entity_type, params)) = best_choice {
            self.entities.insert(
                id,
                RawEntity {
                    id,
                    entity_type,
                    params,
                },
            );
        }
    }

    /// Tokenizes argument lists like `('', #10, (1.0, 2.0, 3.0))`
    fn parse_arg_list(s: &str) -> Vec<StepValue> {
        let mut values = Vec::new();
        let s = s.trim();
        if !s.starts_with('(') || !s.ends_with(')') {
            return values;
        }

        let inner = &s[1..s.len() - 1].trim();
        let chars: Vec<char> = inner.chars().collect();
        let mut i = 0;

        while i < chars.len() {
            while i < chars.len() && (chars[i].is_whitespace() || chars[i] == ',' || chars[i] == ')') {
                i += 1;
            }
            if i >= chars.len() {
                break;
            }

            let start_i = i;
            match chars[i] {
                '\'' => {
                    // String literal
                    i += 1;
                    let start = i;
                    while i < chars.len() && chars[i] != '\'' {
                        i += 1;
                    }
                    let txt: String = chars[start..i].iter().collect();
                    values.push(StepValue::Text(txt));
                    if i < chars.len() {
                        i += 1;
                    }
                }
                '#' => {
                    // Entity reference
                    i += 1;
                    let start = i;
                    while i < chars.len() && chars[i].is_ascii_digit() {
                        i += 1;
                    }
                    let ref_str: String = chars[start..i].iter().collect();
                    if let Ok(id) = ref_str.parse::<u64>() {
                        values.push(StepValue::EntityRef(id));
                    }
                }
                '(' => {
                    // Sub-list
                    let start = i;
                    let mut depth = 0;
                    while i < chars.len() {
                        if chars[i] == '(' {
                            depth += 1;
                        } else if chars[i] == ')' {
                            depth -= 1;
                            if depth == 0 {
                                i += 1;
                                break;
                            }
                        }
                        i += 1;
                    }
                    let sub_str: String = chars[start..i].iter().collect();
                    values.push(StepValue::List(Self::parse_arg_list(&sub_str)));
                }
                '.' => {
                    // Enum: .T., .F., .UNSPECIFIED.
                    i += 1;
                    let start = i;
                    while i < chars.len() && chars[i] != '.' {
                        i += 1;
                    }
                    let enum_str: String = chars[start..i].iter().collect();
                    if i < chars.len() {
                        i += 1;
                    }
                    values.push(StepValue::Enumeration(format!(".{}.", enum_str)));
                }
                _ => {
                    // Number, identifier, or '$' (null)
                    let start = i;
                    while i < chars.len()
                        && chars[i] != ','
                        && chars[i] != ')'
                        && chars[i] != '('
                        && !chars[i].is_whitespace()
                    {
                        i += 1;
                    }
                    let token: String = chars[start..i].iter().collect();
                    if let Ok(num) = token.parse::<f64>() {
                        values.push(StepValue::Number(num));
                    } else if !token.is_empty() && token != "$" {
                        values.push(StepValue::Text(token));
                    }
                }
            }

            // Guarantee progress
            if i == start_i {
                i += 1;
            }
        }

        values
    }

    /// Resolves CARTESIAN_POINT entity
    fn get_point(&self, id: u64) -> Option<Vec3> {
        let ent = self.entities.get(&id)?;
        if ent.entity_type == "CARTESIAN_POINT" && ent.params.len() >= 2 {
            return ent.params[1].as_vec3();
        }
        None
    }

    /// Resolves DIRECTION entity
    fn get_direction(&self, id: u64) -> Option<Vec3> {
        let ent = self.entities.get(&id)?;
        if ent.entity_type == "DIRECTION" && ent.params.len() >= 2 {
            let v = ent.params[1].as_vec3()?;
            return Some(v.normalize());
        }
        None
    }

    /// Resolves AXIS2_PLACEMENT_3D
    fn get_placement(&self, id: u64) -> Option<Axis2Placement3D> {
        let ent = self.entities.get(&id)?;
        if ent.entity_type == "AXIS2_PLACEMENT_3D" && ent.params.len() >= 2 {
            let pt_id = ent.params[1].as_u64()?;
            let location = self.get_point(pt_id).unwrap_or(Vec3::ZERO);

            let axis = if ent.params.len() >= 3 {
                ent.params[2]
                    .as_u64()
                    .and_then(|id| self.get_direction(id))
                    .unwrap_or(Vec3::Z)
            } else {
                Vec3::Z
            };

            let ref_direction = if ent.params.len() >= 4 {
                ent.params[3]
                    .as_u64()
                    .and_then(|id| self.get_direction(id))
                    .unwrap_or(Vec3::X)
            } else {
                Vec3::X
            };

            return Some(Axis2Placement3D {
                location,
                axis,
                ref_direction,
            });
        }
        None
    }

    /// Recursively extracts all entity references from a StepValue
    fn collect_entity_refs(val: &StepValue, out: &mut Vec<u64>) {
        match val {
            StepValue::EntityRef(id) => out.push(*id),
            StepValue::List(l) => {
                for item in l {
                    Self::collect_entity_refs(item, out);
                }
            }
            _ => {}
        }
    }

    /// Extracts all boundary Cartesian points for an ADVANCED_FACE
    fn get_face_boundary_points(
        &self,
        face: &RawEntity,
        vertex_pts: &HashMap<u64, u64>,
        edge_verts: &HashMap<u64, (u64, u64)>,
        loop_edges: &HashMap<u64, Vec<u64>>,
    ) -> Vec<Vec3> {
        let mut boundary_points = Vec::new();
        let mut refs = Vec::new();
        for param in &face.params {
            Self::collect_entity_refs(param, &mut refs);
        }

        for &ref_id in &refs {
            if let Some(edge_ids) = loop_edges.get(&ref_id) {
                for &e_id in edge_ids {
                    if let Some(&(v1, v2)) = edge_verts.get(&e_id) {
                        if let Some(&p1) = vertex_pts.get(&v1) {
                            if let Some(pt) = self.get_point(p1) {
                                boundary_points.push(pt);
                            }
                        }
                        if let Some(&p2) = vertex_pts.get(&v2) {
                            if let Some(pt) = self.get_point(p2) {
                                boundary_points.push(pt);
                            }
                        }
                    }
                }
            } else if let Some(ent) = self.entities.get(&ref_id) {
                if ent.entity_type == "FACE_BOUND" || ent.entity_type == "FACE_OUTER_BOUND" {
                    let mut b_refs = Vec::new();
                    for p in &ent.params {
                        Self::collect_entity_refs(p, &mut b_refs);
                    }
                    for loop_id in b_refs {
                        if let Some(edge_ids) = loop_edges.get(&loop_id) {
                            for &e_id in edge_ids {
                                if let Some(&(v1, v2)) = edge_verts.get(&e_id) {
                                    if let Some(&p1) = vertex_pts.get(&v1) {
                                        if let Some(pt) = self.get_point(p1) {
                                            boundary_points.push(pt);
                                        }
                                    }
                                    if let Some(&p2) = vertex_pts.get(&v2) {
                                        if let Some(pt) = self.get_point(p2) {
                                            boundary_points.push(pt);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        boundary_points
    }

    /// Processes a single surface entity with its exact boundary points
    fn process_surface(&self, surf: &RawEntity, pts: &[Vec3], model: &mut StepModel) {
        let ent_type = &surf.entity_type;

        if ent_type == "CYLINDRICAL_SURFACE" {
            model.stats.cylinders += 1;
            if surf.params.len() >= 3 {
                if let (Some(place_id), Some(radius)) = (surf.params[1].as_u64(), surf.params[2].as_f64()) {
                    let placement = self.get_placement(place_id).unwrap_or(Axis2Placement3D::IDENTITY);
                    let (center, height) = if !pts.is_empty() {
                        let mut t_min = f64::MAX;
                        let mut t_max = f64::MIN;
                        for p in pts {
                            let diff = Vec3::new(p.x - placement.location.x, p.y - placement.location.y, p.z - placement.location.z);
                            let t = diff.dot(placement.axis);
                            if t < t_min { t_min = t; }
                            if t > t_max { t_max = t; }
                        }
                        let h = (t_max - t_min).abs();
                        let actual_h = if h > 0.05 { h } else { 2.0 };
                        let mid_t = (t_min + t_max) * 0.5;
                        let c = Vec3::new(
                            placement.location.x + placement.axis.x * mid_t,
                            placement.location.y + placement.axis.y * mid_t,
                            placement.location.z + placement.axis.z * mid_t,
                        );
                        (c, actual_h)
                    } else {
                        (placement.location, 4.0)
                    };

                    let yaw = placement.axis.x.atan2(placement.axis.z) as f32;
                    let pitch = placement.axis.y.asin() as f32;

                    let part = PackedPart::new(
                        center,
                        radius as f32,
                        height as f32,
                        yaw,
                        pitch,
                        0, // cylinder
                        0, // titanium
                        0,
                    );
                    model.update_bounds(center, radius, height);
                    model.canonical_parts.push(part);
                }
            }
        } else if ent_type == "PLANE" {
            model.stats.planes += 1;
            let place_id = surf.params.get(1).and_then(|v| v.as_u64()).unwrap_or(0);
            let placement = self.get_placement(place_id).unwrap_or(Axis2Placement3D::IDENTITY);

            let (center, half_w, half_l) = if !pts.is_empty() {
                let mut sum_x = 0.0;
                let mut sum_y = 0.0;
                let mut sum_z = 0.0;
                let mut min_x = f64::MAX; let mut max_x = f64::MIN;
                let mut min_y = f64::MAX; let mut max_y = f64::MIN;
                let mut min_z = f64::MAX; let mut max_z = f64::MIN;

                for p in pts {
                    sum_x += p.x; sum_y += p.y; sum_z += p.z;
                    if p.x < min_x { min_x = p.x; } if p.x > max_x { max_x = p.x; }
                    if p.y < min_y { min_y = p.y; } if p.y > max_y { max_y = p.y; }
                    if p.z < min_z { min_z = p.z; } if p.z > max_z { max_z = p.z; }
                }
                let n = pts.len() as f64;
                let c = Vec3::new(sum_x / n, sum_y / n, sum_z / n);
                let dx = (max_x - min_x).abs();
                let dy = (max_y - min_y).abs();
                let dz = (max_z - min_z).abs();

                let mut dims = [dx as f32 * 0.5, dy as f32 * 0.5, dz as f32 * 0.5];
                dims.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
                (c, dims[0].max(0.1), dims[1].max(0.1))
            } else {
                (placement.location, 1.0, 1.0)
            };

            let yaw = placement.axis.x.atan2(placement.axis.z) as f32;
            let pitch = placement.axis.y.asin() as f32;

            let part = PackedPart::new(
                center,
                half_w,
                half_l,
                yaw,
                pitch,
                7, // Shape 7 = Planar Plate / Bounded Plane
                2, // Carbon gunmetal
                0,
            );
            model.update_bounds(center, half_w as f64, half_l as f64);
            model.canonical_parts.push(part);
        } else if ent_type == "CONICAL_SURFACE" {
            model.stats.cones += 1;
            if surf.params.len() >= 4 {
                if let (Some(place_id), Some(radius), Some(semi_angle)) =
                    (surf.params[1].as_u64(), surf.params[2].as_f64(), surf.params[3].as_f64())
                {
                    let placement = self.get_placement(place_id).unwrap_or(Axis2Placement3D::IDENTITY);
                    let yaw = placement.axis.x.atan2(placement.axis.z) as f32;
                    let pitch = placement.axis.y.asin() as f32;
                    let height = if !pts.is_empty() {
                        let mut min_t = f64::MAX;
                        let mut max_t = f64::MIN;
                        for p in pts {
                            let diff = Vec3::new(p.x - placement.location.x, p.y - placement.location.y, p.z - placement.location.z);
                            let t = diff.dot(placement.axis);
                            if t < min_t { min_t = t; }
                            if t > max_t { max_t = t; }
                        }
                        (max_t - min_t).abs().max(0.2)
                    } else {
                        (semi_angle * 10.0).max(1.0)
                    };

                    let part = PackedPart::new(
                        placement.location,
                        radius as f32,
                        height as f32,
                        yaw,
                        pitch,
                        4, // Conical pipe/nozzle
                        2,
                        0,
                    );
                    model.update_bounds(placement.location, radius, height);
                    model.canonical_parts.push(part);
                }
            }
        } else if ent_type == "TOROIDAL_SURFACE" {
            model.stats.torii += 1;
            if surf.params.len() >= 4 {
                if let (Some(place_id), Some(major_r), Some(minor_r)) =
                    (surf.params[1].as_u64(), surf.params[2].as_f64(), surf.params[3].as_f64())
                {
                    let placement = self.get_placement(place_id).unwrap_or(Axis2Placement3D::IDENTITY);
                    let yaw = placement.axis.x.atan2(placement.axis.z) as f32;
                    let pitch = placement.axis.y.asin() as f32;

                    let part = PackedPart::new(
                        placement.location,
                        major_r as f32,
                        minor_r as f32,
                        yaw,
                        pitch,
                        3, // flanged bushing / toroidal ring
                        1, // brass/gold material
                        0,
                    );
                    model.update_bounds(placement.location, major_r + minor_r, minor_r * 2.0);
                    model.canonical_parts.push(part);
                }
            }
        } else if ent_type == "SPHERICAL_SURFACE" {
            model.stats.spheres += 1;
            if surf.params.len() >= 3 {
                if let (Some(place_id), Some(radius)) = (surf.params[1].as_u64(), surf.params[2].as_f64()) {
                    let placement = self.get_placement(place_id).unwrap_or(Axis2Placement3D::IDENTITY);
                    let part = PackedPart::new(
                        placement.location,
                        radius as f32,
                        radius as f32,
                        0.0,
                        0.0,
                        5, // spherical ball joint
                        4, // chrome material
                        0,
                    );
                    model.update_bounds(placement.location, radius, radius);
                    model.canonical_parts.push(part);
                }
            }
        } else if ent_type.contains("B_SPLINE_SURFACE") {
            model.stats.nurbs_surfaces += 1;
            let (center, chord, span) = if !pts.is_empty() {
                let mut sum_x = 0.0; let mut sum_y = 0.0; let mut sum_z = 0.0;
                let mut min_x = f64::MAX; let mut max_x = f64::MIN;
                let mut min_y = f64::MAX; let mut max_y = f64::MIN;
                let mut min_z = f64::MAX; let mut max_z = f64::MIN;

                for p in pts {
                    sum_x += p.x; sum_y += p.y; sum_z += p.z;
                    if p.x < min_x { min_x = p.x; } if p.x > max_x { max_x = p.x; }
                    if p.y < min_y { min_y = p.y; } if p.y > max_y { max_y = p.y; }
                    if p.z < min_z { min_z = p.z; } if p.z > max_z { max_z = p.z; }
                }
                let n = pts.len() as f64;
                let c = Vec3::new(sum_x / n, sum_y / n, sum_z / n);
                let dx = (max_x - min_x).abs();
                let dy = (max_y - min_y).abs();
                let dz = (max_z - min_z).abs();

                let mut dims = [dx as f32 * 0.5, dy as f32 * 0.5, dz as f32 * 0.5];
                dims.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
                (c, dims[0].max(0.2), dims[1].max(0.2))
            } else {
                (Vec3::ZERO, 1.0, 1.0)
            };

            let part = PackedPart::new(
                center,
                chord,
                span,
                0.0,
                0.0,
                6, // Shape 6 = Freeform/Airfoil NURBS surface
                1, // Brass/Gold
                0,
            );
            model.update_bounds(center, chord as f64, span as f64);
            model.canonical_parts.push(part);
        }
    }

    /// Builds the structured StepModel with full B-Rep topological extraction
    pub fn build_model(&self, file_name: String) -> Result<StepModel, String> {
        let mut model = StepModel {
            file_name,
            total_entities: self.entities.len(),
            ..Default::default()
        };

        // 1. Build topological connectivity maps
        let mut vertex_pts: HashMap<u64, u64> = HashMap::new();
        let mut edge_verts: HashMap<u64, (u64, u64)> = HashMap::new();
        let mut loop_edges: HashMap<u64, Vec<u64>> = HashMap::new();

        for ent in self.entities.values() {
            match ent.entity_type.as_str() {
                "VERTEX_POINT" => {
                    if ent.params.len() >= 2 {
                        if let Some(pt_id) = ent.params[1].as_u64() {
                            vertex_pts.insert(ent.id, pt_id);
                        }
                    }
                }
                "EDGE_CURVE" => {
                    if ent.params.len() >= 3 {
                        if let (Some(v1), Some(v2)) = (ent.params[1].as_u64(), ent.params[2].as_u64()) {
                            edge_verts.insert(ent.id, (v1, v2));
                        }
                    }
                }
                "EDGE_LOOP" => {
                    let mut edges = Vec::new();
                    let mut refs = Vec::new();
                    for param in &ent.params {
                        Self::collect_entity_refs(param, &mut refs);
                    }
                    for r in refs {
                        if let Some(oe) = self.entities.get(&r) {
                            if oe.entity_type == "ORIENTED_EDGE" {
                                for p in &oe.params {
                                    if let Some(eid) = p.as_u64() {
                                        if edge_verts.contains_key(&eid) {
                                            edges.push(eid);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    loop_edges.insert(ent.id, edges);
                }
                _ => {}
            }
        }

        let mut processed_surfaces: HashSet<u64> = HashSet::new();

        // 2. Process ADVANCED_FACE entities with boundary loops
        for ent in self.entities.values() {
            if ent.entity_type == "ADVANCED_FACE" {
                let mut refs = Vec::new();
                for p in &ent.params {
                    Self::collect_entity_refs(p, &mut refs);
                }

                // Find surface entity
                let surf_id = refs.iter().cloned().find(|id| {
                    if let Some(se) = self.entities.get(id) {
                        se.entity_type.contains("SURFACE") || se.entity_type == "PLANE"
                    } else {
                        false
                    }
                });

                if let Some(sid) = surf_id {
                    processed_surfaces.insert(sid);
                    let pts = self.get_face_boundary_points(ent, &vertex_pts, &edge_verts, &loop_edges);
                    if let Some(surf_ent) = self.entities.get(&sid) {
                        self.process_surface(surf_ent, &pts, &mut model);
                    }
                }
            } else if ent.entity_type == "MANIFOLD_SOLID_BREP" {
                model.stats.solids += 1;
            }
        }

        // 3. Fallback: Process standalone surfaces not referenced by ADVANCED_FACE
        for ent in self.entities.values() {
            if !processed_surfaces.contains(&ent.id) {
                if ent.entity_type.contains("SURFACE") || ent.entity_type == "PLANE" {
                    self.process_surface(ent, &[], &mut model);
                }
            }
        }

        Ok(model)
    }
}

impl StepModel {
    fn update_bounds(&mut self, pos: Vec3, radius: f64, height: f64) {
        let r = radius.max(0.1);
        let h = height.max(0.1);

        self.bounding_box.min.x = self.bounding_box.min.x.min(pos.x - r);
        self.bounding_box.min.y = self.bounding_box.min.y.min(pos.y - h);
        self.bounding_box.min.z = self.bounding_box.min.z.min(pos.z - r);

        self.bounding_box.max.x = self.bounding_box.max.x.max(pos.x + r);
        self.bounding_box.max.y = self.bounding_box.max.y.max(pos.y + h);
        self.bounding_box.max.z = self.bounding_box.max.z.max(pos.z + r);
    }

    /// Exports the parsed STEP model into our high-speed `.omnicad` binary archive
    pub fn export_to_omnicad<P: AsRef<Path>>(&self, path: P) -> Result<usize, String> {
        let mut archive = OmniCadArchive::new();
        let chunk_size = 2048;
        let num_pages = (self.canonical_parts.len() + chunk_size - 1) / chunk_size;

        for p in 0..num_pages {
            let start = p * chunk_size;
            let end = (start + chunk_size).min(self.canonical_parts.len());
            let mut page = crate::binary_format::SpatialPage::new(p as u32);
            for i in start..end {
                page.add_part(self.canonical_parts[i]);
            }
            archive.pages.push(page);
        }
        archive.total_parts = self.canonical_parts.len();

        let mut file = File::create(path).map_err(|e| e.to_string())?;
        archive.write_to_stream(&mut file).map_err(|e| e.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_step_arg_tokenizer() {
        let s = "('BOLT_SHAFT', #42, (10.0, 20.0, 30.0), .T.)";
        let args = StepParser::parse_arg_list(s);
        assert_eq!(args.len(), 4);
        assert_eq!(args[0], StepValue::Text("BOLT_SHAFT".to_string()));
        assert_eq!(args[1], StepValue::EntityRef(42));
        assert!(matches!(args[2], StepValue::List(_)));
        assert_eq!(args[3], StepValue::Enumeration(".T.".to_string()));
    }

    #[test]
    fn test_step_model_ingestion() {
        let mut parser = StepParser::new();
        let stmts = [
            "#10 = CARTESIAN_POINT('', (0.0, 1.5, 0.0));",
            "#11 = DIRECTION('', (0.0, 1.0, 0.0));",
            "#12 = DIRECTION('', (1.0, 0.0, 0.0));",
            "#20 = AXIS2_PLACEMENT_3D('', #10, #11, #12);",
            "#30 = CYLINDRICAL_SURFACE('', #20, 2.5);",
        ];
        for stmt in stmts {
            parser.parse_statement(stmt);
        }

        let model = parser.build_model("test_assembly.stp".to_string()).unwrap();
        assert_eq!(model.stats.cylinders, 1);
        assert_eq!(model.canonical_parts.len(), 1);
        assert_eq!(model.canonical_parts[0].pos_x, 0.0);
        assert_eq!(model.canonical_parts[0].pos_y, 1.5);
        assert_eq!(model.canonical_parts[0].pos_z, 0.0);
        assert_eq!(model.canonical_parts[0].param0, 2.5);
    }
}
