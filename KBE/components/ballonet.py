"""
Class representing the ballonet of the airship, which is an air-filled bag inside the main envelope. 
By inflating or deflating it, the airship can control its volume, pressure, and altitude.
"""


from parapy.core import Base, Input, Part, Attribute
from parapy.geom import Sphere, SubtractedSolid, Point, translate, Position
import math

class Ballonet(Base):

    radius= Input(5.0)
    thickness= Input(0.1)
    bpm2= Input(5)
    envelope_radius= Input(10.0)
    envelope_thickness = Input(0.1)
    ambient_gas_density_sl = Input(1.225)

    @Attribute
    def ballonet_z_offset(self):
        return -(self.envelope_radius - self.envelope_thickness - self.radius)

    @Attribute
    def ballonet_center(self):
        return Position(Point(0, 0, self.ballonet_z_offset))

    @Attribute
    def ballonet_volume_fraction_sl(self):
        V_envelope_total = (4.0 / 3.0) * math.pi * self.envelope_radius ** 3
        V_envelope_shell = 4.0 * math.pi * self.envelope_radius ** 2 * self.envelope_thickness
        V_interior = V_envelope_total - V_envelope_shell

        V_ballonet = (4.0 / 3.0) * math.pi * self.radius ** 3

        fraction = V_ballonet / V_interior

        if not (0.0 < fraction < 1.0):
            raise ValueError(
                f"Computed ballonet_volume_fraction_sl = {fraction:.4f} is outside (0, 1). "
                f"Check that ballonet_radius ({self.radius} m) is smaller than "
                f"the envelope interior (r_env={self.envelope_radius} m, "
                f"t_env={self.thickness} m)."
            )

        return fraction


    @Part
    def outer_sphere(self):
        return Sphere(
            radius=self.radius,
            position=self.ballonet_center,
            color='orange',
            hidden=True
        )

    @Part
    def inner_sphere(self):
        return Sphere(
            radius=max(self.radius - self.thickness, 0.0),
            position=self.ballonet_center,
            color='orange',
            hidden=True
        )

    @Part
    def shape(self):
        return SubtractedSolid(
            shape_in=self.outer_sphere,
            tool=self.inner_sphere,
            color='orange',
            transparency=0.0
        )

    @Attribute
    def weight(self):
        import math
        return 4 * math.pi * self.radius**2 * self.bpm2

    @Attribute
    def cog(self):
        return Point(0, 0, self.ballonet_z_offset)

    @Attribute
    def gas_mass(self):
        # Mass of ambient air inside the ballonet [kg], derived from geometry.
        r = self.radius
        t = self.thickness

        v_ballonet_total = (4.0 / 3.0) * math.pi * r ** 3
        v_ballonet_shell = 4.0 * math.pi * r ** 2 * t
        v_ballonet_interior = v_ballonet_total - v_ballonet_shell

        if v_ballonet_interior <= 0.0:
            raise ValueError(
                f"Ballonet interior volume is {v_ballonet_interior:.4f} m³ — "
                f"thickness ({t} m) is too large for radius ({r} m)."
            )

        return self.ambient_gas_density_sl * v_ballonet_interior

    @Attribute
    def inertia(self):
        import math
        r_o = self.radius
        r_i = max(self.radius - self.thickness, 0.0)
        
        if r_o != r_i:
            I_shell = (2/5) * self.weight * (r_o**5 - r_i**5) / (r_o**3 - r_i**3)
        else:
            I_shell = (2/3) * self.weight * r_o**2  

        I_gas = (2/5) * self.gas_mass * r_i**2

        total = I_shell + I_gas
        return {"Ixx": total, "Iyy": total, "Izz": total}
    
    