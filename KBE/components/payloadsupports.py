from parapy.core import Base, Input, Attribute, Part, child
from parapy.geom import Cylinder, Position
import math


class SinglePayloadPatch(Base):
    envelope_thickness= Input(0.1)
    envelope_radius= Input(10.0)
    payload_load_patch_radius = Input(0.5)
    payload_load_patch_loc= Input(0.7)
    load_patch_thickness= Input(0.04)
    cluster_index= Input(0)

    @Attribute
    def _inner_radius(self):
        return self.envelope_radius

    @Attribute
    def _polar(self):
        return math.acos(max(-1.0, min(1.0, -self.payload_load_patch_loc)))

    @Attribute
    def _azimuth(self):
        if self.cluster_index == 0:
            return math.pi/4
        elif self.cluster_index == 1:
            return math.pi + math.pi/4
        elif self.cluster_index == 2:
            return math.pi / 2 + math.pi/4
        else:
            return -math.pi / 2 + math.pi / 4

    @Attribute
    def _patch_position(self):
        R= self._inner_radius
        polar= self._polar
        azimuth = self._azimuth
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
            radius=self.payload_load_patch_radius,
            height=self.load_patch_thickness,
            centered=True,
            position=self._patch_position,
            color="white",
        )

    @Attribute
    def shape(self):
        return self.disc


class PayloadSupports(Base):
    envelope_thickness= Input(0.1)
    envelope_radius= Input(10.0)
    payload_load_patch_radius = Input(0.5)
    payload_load_patch_loc= Input(0.7)
    load_patch_thickness= Input(0.04)

    @Part
    def patches(self):
        return SinglePayloadPatch(
            quantify=4,
            envelope_thickness=self.envelope_thickness,
            envelope_radius=self.envelope_radius,
            payload_load_patch_radius=self.payload_load_patch_radius,
            payload_load_patch_loc=self.payload_load_patch_loc,
            load_patch_thickness=self.load_patch_thickness,
            cluster_index=child.index,
        )

    @Attribute
    def shape(self):
        return [p.disc for p in self.patches]