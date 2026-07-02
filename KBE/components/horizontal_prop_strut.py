import math
from parapy.core import Base, Input, Part, child, Attribute
from parapy.geom import Cylinder, Position, ExtrudedSolid, Point, Wire, LineSegment, XOY
from components.load_patch_h import LoadPatchHorizontal
import warnings


class Strut(Base):
    radius= Input(0.05)
    height= Input(1.0)
    position= Input(XOY)
    color= Input('white')
    material_density = Input(1600.0)   

    @Part
    def cylinder(self):
        return Cylinder(
            radius=self.radius,
            height=self.height,
            position=self.position,
            color=self.color,
        )

    @Attribute
    def volume(self):
        return math.pi * self.radius**2 * self.height

    @Attribute
    def weight(self):
        return self.material_density * self.volume

    @Attribute
    def cog(self):

        p  = self.position.location
        vz = self.position.Vz
        return Point(
            p.x +vz.x * self.height / 2,
            p.y+vz.y *self.height / 2,
            p.z + vz.z* self.height / 2,
        )

    @Attribute
    def inertia(self):
        m, r, h = self.weight, self.radius, self.height
        I_lat = (1 / 12) * m * (3 * r**2 + h**2) 
        I_ax  = 0.5 * m * r**2                    
        return {"Ixx": I_lat, "Iyy": I_lat, "Izz": I_ax}


class MainStrut(Base):
    strut_size= Input(1.0)
    position= Input(XOY)
    color= Input('steelblue')
    material_density = Input(1600.0)   # kg/m³

    @Attribute
    def _p1(self):
        return self.position.translate('x', -self.strut_size / 10).location

    @Attribute
    def _p2(self):
        return self.position.translate('x',  self.strut_size / 10).location

    @Attribute
    def _p3(self):
        return self.position.translate('y',  self.strut_size).location

    @Part(parse=False)
    def _wire(self):
        return Wire(
            curves_in=[
                LineSegment(start=self._p1, end=self._p2),
                LineSegment(start=self._p2, end=self._p3),
                LineSegment(start=self._p3, end=self._p1),
            ],
            hidden=True,
        )

    @Part(parse=False)
    def shape(self):
        return ExtrudedSolid(
            island=self._wire,
            distance=self.strut_size * 0.02,
            direction=self.position.Vz,
            color=self.color,
        )

    @Attribute
    def volume(self):

        base= self.strut_size / 5
        h_tri =self.strut_size
        depth = self.strut_size * 0.02
        return 0.5 * base * h_tri * depth

    @Attribute
    def weight(self):
        return self.material_density * self.volume

    @Attribute
    def cog(self):
        p = self.position.location
        vy = self.position.Vy
        vz = self.position.Vz
        cy = self.strut_size / 3        
        cz = self.strut_size * 0.01    
        return Point(
            p.x + vy.x * cy + vz.x * cz,
            p.y + vy.y * cy + vz.y * cz,
            p.z + vy.z * cy + vz.z * cz,
        )

    @Attribute
    def inertia(self):
        m = self.weight
        b = self.strut_size / 5         
        h = self.strut_size             
        d = self.strut_size * 0.02      

        Ixx = m * (h**2 / 18 + d**2 / 12)
        Iyy = m * (b**2 / 18 + d**2 / 12)
        Izz = m * (b**2 / 18 + h**2 / 18)
        return {"Ixx": Ixx, "Iyy": Iyy, "Izz": Izz}


class StrutCluster(Base):
    strut_radius= Input(0.05)
    strut_size= Input(1.0)
    position= Input(XOY)
    cluster_index= Input(0)
    horizontal_propulsor_loc = Input(0.0)
    envelope_radius= Input(10.0)
    material_density= Input(1600.0)


    @property
    def _attach_height(self):
        return 0.45 * self.strut_size

    @property
    def _sub_strut_length(self):
        return 1.2 * self._attach_height * math.sqrt(2)

    @property
    def _radius_true(self):
        return self.envelope_radius * math.sqrt(1 - self.horizontal_propulsor_loc**2)

    def _sub_strut_angle(self, index):
        base_angle = math.pi - math.pi / 4
        if self.cluster_index in (0, 1, 2, 3):
            horizontal_to_sphere  = self.envelope_radius - self._radius_true
            horizontal_to_equator = (
                self.horizontal_propulsor_loc * self.envelope_radius - self._attach_height
            )
            geometric_correction  = math.atan2(
                horizontal_to_sphere, max(horizontal_to_equator, 1e-6)
            )
            inner = 1.0 - (1 * self.strut_size + self.strut_radius) / self.envelope_radius
            loc_90 = math.sqrt(1.0 - inner**2)
            geometric_correction2 = (math.pi / 4) * (self.horizontal_propulsor_loc / loc_90)

            if self.cluster_index in (0, 1, 2):
                if index == 0: return base_angle + geometric_correction
                if index==1: return base_angle
                if index ==2:return base_angle - geometric_correction2
                return base_angle
            else:
                if index ==0: return base_angle -geometric_correction2
                if index == 1: return base_angle
                if index==2: return base_angle + geometric_correction
                return base_angle
        return base_angle

    def _sub_strut_position(self, index):
        angle = index * math.pi / 2
        return (
            self.position
            .translate("z", self._attach_height)
            .rotate("z", angle + math.pi / 2)
            .rotate("y", self._sub_strut_angle(index))
        )

    @Part
    def main_strut(self):
        return MainStrut(
            strut_size=self.strut_size,
            position=self.position.rotate90("x"),
            color='ivory',
            material_density=self.material_density,
        )

    @Part
    def sub_struts(self):
        return Strut(
            quantify=4,
            radius=self.strut_radius,
            height=self._sub_strut_length,
            position=self._sub_strut_position(child.index),
            color='ivory',
            material_density=self.material_density,
        )

    @Attribute
    def shape(self):
        return [self.main_strut.shape] + [s.cylinder for s in self.sub_struts]



    @Attribute
    def weight(self):
        return self.main_strut.weight + sum(s.weight for s in self.sub_struts)

    @Attribute
    def cog(self):
        components = (
            [(self.main_strut.weight, self.main_strut.cog)]
            + [(s.weight, s.cog) for s in self.sub_struts]
        )
        total_w = self.weight
        return Point(
            sum(w * p.x for w, p in components) / total_w,
            sum(w * p.y for w, p in components) / total_w,
            sum(w * p.z for w, p in components) / total_w,
        )

    @Attribute
    def inertia(self):
        ref= self.cog
        Ixx = Iyy = Izz = 0.0
        entries = (
            [(self.main_strut.weight, self.main_strut.cog, self.main_strut.inertia)]
            + [(s.weight, s.cog, s.inertia) for s in self.sub_struts]
        )
        for m, c, I in entries:
            dx, dy, dz = c.x - ref.x, c.y - ref.y, c.z - ref.z
            Ixx += I["Ixx"] + m * (dy**2 + dz**2)
            Iyy += I["Iyy"] + m * (dx**2 + dz**2)
            Izz += I["Izz"] + m * (dx**2 + dy**2)
        return {"Ixx": Ixx, "Iyy": Iyy, "Izz": Izz}


class StrutSupportH(Base):
    envelope_radius= Input(10)
    envelope_thickness= Input(0.1)
    position= Input(XOY)
    strut_size= Input(1.0)
    strut_radius= Input(0.05)
    horizontal_propulsor_loc = Input(0)
    material_density= Input(1600.0)


    @Attribute
    def _radius_true(self):
        return self.envelope_radius * math.sqrt(1 - self.horizontal_propulsor_loc**2)

    def _cluster_position(self, index):
        tx = self._radius_true if index == 0 else -self._radius_true if index == 1 else 0
        ty = self._radius_true if index == 2 else -self._radius_true if index == 3 else 0
        rx = -math.pi / 2 if index == 2 else math.pi / 2 if index == 3 else 0
        ry = -math.pi / 2 if index == 0 else math.pi / 2 if index == 1 else 0
        return (
            self.position
            .translate("x", tx).translate("y", ty)
            .rotate("x", rx).rotate("z", ry).rotate("x", ry)
            .rotate("y", math.pi if child.index == 1 else 0)
            .rotate("z", math.pi if child.index == 1 else 0)
            .translate("y",  self.horizontal_propulsor_loc * self.envelope_radius if index in (0, 1, 2) else 0)
            .translate("y", -self.horizontal_propulsor_loc * self.envelope_radius if index == 3 else 0)
        )

    @Part
    def clusters(self):
        return StrutCluster(
            quantify=2,
            strut_radius=self.strut_radius,
            strut_size=self.strut_size,
            cluster_index=child.index,
            horizontal_propulsor_loc=self.horizontal_propulsor_loc,
            envelope_radius=self.envelope_radius,
            position=self._cluster_position(child.index),
            material_density=self.material_density,
        )

    @Part
    def load_patches(self):
        return LoadPatchHorizontal(
            quantify=2,
            envelope_radius=self.envelope_radius,
            envelope_thickness=self.envelope_thickness,
            strut_size=self.strut_size,
            strut_radius=self.strut_radius,
            horizontal_propulsor_loc=self.horizontal_propulsor_loc,
            cluster_index=child.index,
            material_density=self.material_density, 
        )

    @Attribute
    def shape(self):
        strut_shapes= [shape for cluster in self.clusters for shape in cluster.shape]
        patch_shapes = [p.disc for p in self.load_patches]
        return strut_shapes + patch_shapes

    @Attribute
    def weight(self):
        return (sum(c.weight for c in self.clusters)
              + sum(p.weight for p in self.load_patches))

    @Attribute
    def cog(self):
        components = (
            [(c.weight, c.cog) for c in self.clusters]
          + [(p.weight, p.cog) for p in self.load_patches]
        )
        total_w = self.weight
        return Point(
            sum(w * pt.x for w, pt in components) / total_w,
            sum(w * pt.y for w, pt in components) / total_w,
            sum(w * pt.z for w, pt in components) / total_w,
        )

    @Attribute
    def inertia(self):
        ref = self.cog
        Ixx = Iyy = Izz = 0.0
        entries = (
            [(c.weight, c.cog, c.inertia) for c in self.clusters]
          + [(p.weight, p.cog, p.inertia) for p in self.load_patches]
        )
        for m, c, I in entries:
            dx, dy, dz = c.x - ref.x, c.y - ref.y, c.z - ref.z
            Ixx += I["Ixx"] + m * (dy**2 + dz**2)
            Iyy += I["Iyy"] + m * (dx**2 + dz**2)
            Izz += I["Izz"] + m * (dx**2 + dy**2)
        return {"Ixx": Ixx, "Iyy": Iyy, "Izz": Izz}