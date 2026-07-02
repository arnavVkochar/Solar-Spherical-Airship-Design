from parapy.core import Base, Input, Attribute, Part, child
from parapy.geom import Box, Position
import math
from parapy.geom import Point


class SolarPanel(Base):
    solar_panel_eta = Input(0.33)
    area_per_panel = Input(1.0)
    req_area= Input(200.0)
    envelope_radius = Input(10.0)
    position= Input(Position())
    min_ring_fraction= Input(0.15)
    ring_spacing_factor= Input(1)
    sweight= Input(2)
    azimuth_spacing_factor= Input(1.1)

    @Attribute
    def num(self):
        return math.ceil(self.req_area / self.area_per_panel)

    @Attribute
    def side(self):
        return math.sqrt(self.area_per_panel)

    @Attribute
    def _min_ring_radius(self):
        # Absolute radius of the first (innermost) ring [m]
        return self.envelope_radius * self.min_ring_fraction

    @Attribute
    def _ring_layout(self):
        """
        Distributes panels in concentric latitude rings over the upper hemisphere.
        Each ring is defined by its projected radius, z-height, and panel count.

        How do we do it? We:
          1. Place a single cap panel at the north pole (r=0, z=R).
          2. Step polar angle outward by arc_step = side / R per ring.
          3. At each ring compute how many panels fit around the circumference.
          4. Stop when all panels are placed.
        """
        R= self.envelope_radius
        side= self.side
        rings = []
        panels_remaining = self.num

        rings.append({'ring_radius': 0.0, 'z_height': R, 'count': 1})
        panels_remaining -= 1

        if panels_remaining <= 0:
            return rings

        min_r= self.envelope_radius * self.min_ring_fraction
        current_polar = math.asin(min_r / R)
        arc_step= (side * self.ring_spacing_factor) / R

        while panels_remaining > 0:
            current_radius = R * math.sin(current_polar)
            z = R * math.cos(current_polar)

            if current_polar >= math.pi / 2:
                current_radius = R
                z = 0.0
                capacity = panels_remaining
            else:
                circumference = 2 * math.pi * current_radius
                capacity = max(1, math.floor(
                    circumference / (side * self.azimuth_spacing_factor)
                ))

            count = min(capacity, panels_remaining)
            rings.append({'ring_radius': current_radius, 'z_height': z, 'count': count})
            panels_remaining -= count
            current_polar += arc_step

        return rings

    @Attribute
    def _panel_positions(self):
        R= self.envelope_radius
        positions = []

        for ring in self._ring_layout:
            r= ring['ring_radius']
            z= ring['z_height']
            count = ring['count']

            if r == 0.0:
                positions.append(self.position.translate("z", R))
            else:
                polar = math.atan2(r, z)
                for j in range(count):
                    angle = 2 * math.pi * j / count
                    pos = (
                        self.position
                        .translate("x", r * math.cos(angle))
                        .translate("y", r * math.sin(angle))
                        .translate("z", z)
                        .rotate('z', angle)
                        .rotate('y', polar)
                    )
                    positions.append(pos)

        return positions

    @Part
    def panels(self):
        return Box(
            color=(0, 51, 102),
            quantify=self.num,
            centered=True,
            length=self.side,
            width=self.side,
            height=0.02,
            position=self._panel_positions[child.index]
        )

    @Attribute
    def shape(self):
        return [p for p in self.panels]

    @Attribute
    def weight(self):
        return self.sweight * self.num

    @Attribute
    def cog(self):
        points = [p.position.point for p in self.panels]
        x= sum(pt.x for pt in points) / len(points)
        y =sum(pt.y for pt in points) / len(points)
        z =sum(pt.z for pt in points) / len(points)
        return (x, y, z)

    @Attribute
    def cog(self):
        
        points = [p.position.point for p in self.panels]
        x =sum(pt.x for pt in points) / len(points)
        y= sum(pt.y for pt in points) / len(points)
        z=sum(pt.z for pt in points) / len(points)
        return Point(x, y, z)
    
    @Attribute
    def inertia(self):
        Ixx =Iyy = Izz = 0.0
        s = self.side
        t = 0.02
        for panel in self.panels:
            Ixx += (1/12) * self.sweight * (s**2 + t**2)
            Iyy += (1/12) * self.sweight * (s**2 + t**2)
            Izz += (1/12) * self.sweight * (s**2 + s**2)
        return {"Ixx": Ixx, "Iyy": Iyy, "Izz": Izz}