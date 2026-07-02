
from parapy.core import Base, Input, Attribute, Part
from parapy.geom import Cylinder, Position
import math


class LoadPatchHorizontal(Base):
    envelope_thickness= Input(0.1)
    envelope_radius= Input(10.0)
    strut_size= Input(0.5)
    strut_radius= Input(0.05)
    horizontal_propulsor_loc = Input(0.0)
    cluster_index= Input(0)
    thickness= Input(0.04)
    material_density = Input(1600.0)

    @Attribute
    def _vertical_offset(self):
        return -self.strut_size*self.horizontal_propulsor_loc/2

    @Attribute
    def _radius_offset(self):
        return self.strut_size * self.horizontal_propulsor_loc/2



    @Attribute
    def _inner_radius(self):
        return self.envelope_radius - self.envelope_thickness

    @Attribute
    def _attach_height(self):
        return 0.45 * self.strut_size

    @Attribute
    def _sub_strut_length(self):
        return 1.2 * self._attach_height* math.sqrt(2)

    @Attribute
    def _radius_true(self):
        return self._inner_radius* math.sqrt(
            1.0 - self.horizontal_propulsor_loc ** 2
        )



    @Attribute
    def patch_radius(self):

        attach_height= 0.45 * self.strut_size
        sub_strut_length = 1.2 * attach_height * math.sqrt(2)
        base_angle = math.pi - math.pi / 4
        h_to_sphere= self._inner_radius - self._inner_radius
        h_to_equator = 0.0 * self.envelope_radius - attach_height - 0.0
        gc_bottom= math.atan2(h_to_sphere, max(h_to_equator, 1e-6))
        angle_bottom = base_angle + gc_bottom


        inner = 1.0 - (self.strut_size + self.strut_radius) / self.envelope_radius
        loc_90 = math.sqrt(max(1.0 - inner ** 2, 0.0))
        gc_top= (math.pi / 4) * (0.0 / max(loc_90, 1e-9))
        angle_top= base_angle - gc_top

        tip_bottom= attach_height - math.cos(angle_bottom) * sub_strut_length
        tip_top= attach_height - math.cos(angle_top)    * sub_strut_length

        span=abs(tip_bottom - tip_top)
        base =self.strut_size * 0.45 * 1.2
        return max(base, span / 2.0)+self._radius_offset

    @Attribute
    def _polar(self):

        loc = -self.horizontal_propulsor_loc

        offset_angle = math.asin(
            max(-1.0, min(1.0, self._vertical_offset / self._inner_radius))
        )
        raw_angle= math.acos(max(-1.0, min(1.0, loc)))
        return raw_angle + offset_angle

    @Attribute
    def _azimuth(self):

        if self.cluster_index == 0:
            return 0.0
        elif self.cluster_index == 1:
            return math.pi
        elif self.cluster_index == 2:
            return math.pi / 2
        else:
            return -math.pi / 2


    @Attribute
    def _angle_bottom(self):

        base_angle= math.pi - math.pi / 4
        horizontal_to_sphere  = self._inner_radius - self._radius_true
        horizontal_to_equator = (
            -self.horizontal_propulsor_loc * self.envelope_radius
            - self._attach_height
            - self._vertical_offset
        )
        geometric_correction= math.atan2(
            horizontal_to_sphere,
            max(horizontal_to_equator, 1e-6)
        )
        return base_angle+ geometric_correction

    @Attribute
    def _angle_top(self):

        base_angle = math.pi - math.pi / 4
        inner= 1.0 - (self.strut_size + self.strut_radius) / self.envelope_radius
        loc_90 = math.sqrt(max(1.0 - inner ** 2, 0.0))
        geometric_correction2 = (math.pi / 4) * (
            -self.horizontal_propulsor_loc / max(loc_90, 1e-9)
        )
        return base_angle- geometric_correction2


    @Attribute
    def _patch_position(self):
        R= self._inner_radius
        polar= self._polar
        azimuth= self._azimuth
        r_xy= R * math.sin(polar)
        z= R * math.cos(polar)
        return (
            Position()
            .translate("x", r_xy * math.cos(azimuth))
            .translate("y", r_xy * math.sin(azimuth))
            .translate("z", z)
            .rotate("z", azimuth)
            .rotate("y", polar)
        )

    @Part
    def disc(self):
        return Cylinder(
            radius=self.patch_radius,
            height=self.thickness,
            centered=True,
            position=self._patch_position,
            color="white",
        )

    @Attribute
    def shape(self):
        return self.disc
    

    @Attribute
    def weight(self):

        volume= math.pi* self.patch_radius**2 * self.thickness
        return self.material_density * volume

    @Attribute
    def cog(self):

        pos= self._patch_position
        return pos.location 

    @Attribute
    def inertia(self):
        m, r, h = self.weight, self.patch_radius, self.thickness
        I_lat = (1 / 12) * m * (3 * r**2 + h**2)  
        I_ax= 0.5 * m * r**2
        return {"Ixx": I_lat, "Iyy": I_lat, "Izz": I_ax}