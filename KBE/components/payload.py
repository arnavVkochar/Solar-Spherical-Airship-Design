from parapy.core import Base, Input, Part, Attribute
from parapy.geom import Box
import warnings


def generate_warning(warning_header, msg):
    from tkinter import Tk, messagebox
    window = Tk()
    window.withdraw()
    messagebox.showwarning(warning_header, msg)
    window.deiconify()
    window.destroy()
    window.quit()


class Payload(Base):
    envelope_radius = Input(10.0)
    length= Input(4.0)
    width= Input(2.0)
    height= Input(2.0)
    payload_d_factor = Input(1.15)
    pweight= Input(200)

    @Attribute
    def effective_d_factor(self):
        if self.payload_d_factor < 1.0:
            msg = ("payload_d_factor cannot be less than 1.0. "
                   "Value will be set to 1.0.")
            generate_warning("Warning: Value changed", msg)
            self.payload_d_factor = 1.0
            return 1.0
        return self.payload_d_factor

    @Attribute
    def payload_position(self):
        from parapy.geom import Point, Position
        z = -(self.envelope_radius + self.effective_d_factor * self.height / 2)
        return Position(Point(0, 0, z))

    @Part
    def shape(self):
        return Box(
            length=self.length,
            width=self.width,
            height=self.height,
            centered=True,
            color="orange",
            position=self.payload_position
        )

    @Attribute
    def weight(self):
        return self.pweight

    @Attribute
    def cog(self):
        return self.shape.position.point

    @Attribute
    def inertia(self):
        m, l, w, h = self.pweight, self.length, self.width, self.height
        return {
            "Ixx": (1/12) * m * (w**2 + h**2),
            "Iyy": (1/12) * m * (l**2 + h**2),
            "Izz": (1/12) * m * (l**2 + w**2),
        }