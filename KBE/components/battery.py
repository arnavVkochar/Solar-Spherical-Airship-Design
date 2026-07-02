from parapy.core import Base, Input, Part, Attribute
from parapy.geom import Box


class Battery(Base):

    length = Input(2.0)
    width = Input(1.5)
    height = Input(1.5)
    position = Input()
    bwpuv = Input(1.5)
    nob = Input(2)

    @Part
    def shape(self):
        return Box(
            length=self.length * self.nob,
            width=self.width,
            centered=True,
            height=self.height,
            position=self.position
        )
    
    @Attribute
    def weight(self):
        return self.bwpuv*self.length*self.width*self.height*self.nob
    
    @Attribute
    def cog(self):
        # Box is centered, so CoG = center = position point
        return self.shape.position.point
    
    @Attribute
    def inertia(self):
        m  = self.weight
        bl = self.length * self.nob   # stacked along length
        bw = self.width
        bh = self.height
        return {
            "Ixx": (1/12) * m * (bw**2 + bh**2),
            "Iyy": (1/12) * m * (bl**2 + bh**2),
            "Izz": (1/12) * m * (bl**2 + bw**2),
        }