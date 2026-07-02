#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import radians, tan
import pandas as pd
from Optimizer.Optim_modules.propeller_weight import run_model as compute_prop_weight

from parapy.geom import (GeomBase, translate, Point, FittedCurve, rotate,
                         XOY, TransformedCurve, ScaledCurve,
                         LoftedSurface, LoftedSolid, RotatedCurve, Cylinder)
from parapy.core import Base, Part, Input, Attribute, child
from parapy.geom import Position
from parapy.geom import Cylinder, Box, Position, Fused
import math

def _read_blade_table(filepath: str) -> list:

    df = pd.read_excel(filepath, header=None)
    df = df.dropna(how='all').reset_index(drop=True)

    if df.shape[1] < 3:
        raise ValueError(f"Excel file must have at least 3 columns; got {df.shape[1]}.")
    if not pd.api.types.is_numeric_dtype(df.iloc[0, 0]):
        df = df.iloc[1:].reset_index(drop=True)

    df = df.iloc[:, :3].astype(float)
    df.columns = ['r_R', 'c_ctip', 'twist']

    if df['r_R'].min() < 0 or df['r_R'].max() > 1:
        raise ValueError("r/R_tip values must be in [0, 1].")
    if (df['c_ctip'] <= 0).any():
        raise ValueError("c/c_tip values must all be positive.")

    df = df.sort_values('r_R').reset_index(drop=True)
    return list(df.itertuples(index=False, name=None))


class BladeSection(GeomBase):

    airfoil_curve: object = Input()
    chord: float = Input()
    twist_deg: float = Input()
    span_y: float = Input()
    sweep_x: float = Input()
    mesh_deflection: float = Input(1e-4)

    @Part
    def _unit_positioned(self):
        return TransformedCurve(
            curve_in=self.airfoil_curve,
            from_position=rotate(translate(XOY, 'x', 1), 'x', -90, deg=True),
            to_position=translate(self.position,
                                  'y', self.span_y,
                                  'x', self.sweep_x),
            hidden=True
        )

    @Part
    def _scaled(self):
        return ScaledCurve(
            curve_in=self._unit_positioned,
            reference_point=self._unit_positioned.start,
            factor=self.chord,
            mesh_deflection=self.mesh_deflection,
            hidden=True
        )

    @Part
    def curve(self):
        return RotatedCurve(
            curve_in=self._scaled,
            rotation_point=self._scaled.start,
            vector=self.position.Vy,
            angle=radians(self.twist_deg),
            mesh_deflection=self.mesh_deflection
        )



class Blade(GeomBase):

    R_tip: float = Input()
    c_tip: float = Input()
    hub_radius: float = Input(0.0)  # <-- added
    sweep_TE: float = Input(0.0)
    airfoil_file: str = Input()
    blade_data_file_vertical: str = Input()
    mesh_deflection: float = Input(1e-4)

    @Attribute
    def blade_table(self) -> list:
        return _read_blade_table(self.blade_data_file_vertical)

    @Attribute
    def n_sections(self) -> int:
        return len(self.blade_table)

    @Attribute
    def _airfoil_pts(self) -> list:
        with open(self.airfoil_file, 'r') as f:
            pts = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    x, y = line.split(None, 1)
                    pts.append(Point(float(x), float(y)))
                except ValueError:
                    continue
        return pts

    @Part
    def _base_airfoil(self):
        return FittedCurve(points=self._airfoil_pts,
                           mesh_deflection=self.mesh_deflection,
                           hidden=True)

    @Part
    def sections(self):
        return BladeSection(
            quantify=self.n_sections,
            airfoil_curve=self._base_airfoil,
            chord=self.c_tip * self.blade_table[child.index][1],
            twist_deg=self.blade_table[child.index][2],
            span_y=self.hub_radius + self.R_tip * self.blade_table[child.index][0],  # <-- offset added
            sweep_x=((self.hub_radius + self.R_tip * self.blade_table[child.index][0])
                     * tan(radians(self.sweep_TE))),  # <-- sweep also offset consistently
            mesh_deflection=self.mesh_deflection,
            position=self.position
        )

    @Attribute
    def _section_curves(self) -> list:
        return [sec.curve for sec in self.sections]

    @Part
    def blade_surface(self):
        return LoftedSurface(
            profiles=self._section_curves,
            mesh_deflection=self.mesh_deflection
        )

    @Part
    def blade_solid(self):
        return LoftedSolid(
            profiles=self._section_curves,
            mesh_deflection=self.mesh_deflection
        )



class Propeller(GeomBase):

    hub_radius: float = Input(0.08)
    R_tip: float = Input(1.0)
    c_tip: float = Input(0.2)
    vertical_num_blades: int = Input(3)
    sweep_TE: float = Input(0.0)
    airfoil_file: str = Input()
    blade_data_file_vertical: str = Input()
    mesh_deflection: float = Input(1e-4)

    @Part
    def hub(self):

        return Cylinder(
            radius=self.hub_radius,
            height=self.c_tip*4,
            centered=True,
            color='red',
            position=self.position.rotate90('x' if child.index in (2, 3) else 'y')
        )

    @Part
    def blades(self):
        return Blade(
            quantify=self.vertical_num_blades,
            R_tip=self.R_tip,
            c_tip=self.c_tip,
            hub_radius=self.hub_radius,
            sweep_TE=self.sweep_TE,
            airfoil_file=self.airfoil_file,
            blade_data_file_vertical=self.blade_data_file_vertical,
            mesh_deflection=self.mesh_deflection,
            position=rotate(
                self.position.translate("x", self.c_tip*2),  # <-- only change
                'x' if child.index in (2, 3) else 'x',
                child.index * 360.0 / self.vertical_num_blades,
                deg=True
            ),
            color='orange',
            label=f'blade_{child.index}'
        )

    @Attribute
    def shape(self):
        return Fused(
            shape_in=self.hub,
            tool=[b.blade_solid for b in self.blades]
        )


class VerticalPropulsion(Base):

    vertical_propulsor_loc = Input(0)
    radius: float = Input(1.0)
    envelope_radius: float = Input()
    position: object = Input()
    strut_size: float = Input()
    vertical_num_blades: int = Input(3)

    hub_to_tip_v = Input(0.2)

    c_tip: float = Input(0.08)
    sweep_TE: float = Input(0.0)
    airfoil_file: str = Input()
    blade_data_file_vertical: str = Input()
    mesh_deflection: float = Input(1e-4)

    @Attribute
    def radius_true(self):

        cross_section_radius = self.envelope_radius * math.sqrt(1 - self.vertical_propulsor_loc ** 2)
        return cross_section_radius + self.strut_size

    @Attribute
    def weight(self):

        result = compute_prop_weight({
            "excel_path": self.blade_data_file_vertical,
            "prop_radius_m": self.radius,
            "blade_count": self.vertical_num_blades,
            "hub_to_tip": self.hub_to_tip_v,
        })
        return result["total_assembly_weight_kg"]

    @Part
    def propulsors(self):
        return Propeller(
            quantify=4,
            R_tip=self.radius,
            c_tip=self.c_tip,
            vertical_num_blades=self.vertical_num_blades,
            sweep_TE=self.sweep_TE,
            airfoil_file=self.airfoil_file,
            blade_data_file_vertical=self.blade_data_file_vertical,
            mesh_deflection=self.mesh_deflection,
            position=(
                self.position
                .translate(
                    "x",
                    self.radius_true if child.index == 0 else
                    -self.radius_true if child.index == 1 else 0
                )
                .translate(
                    "y",
                    self.radius_true if child.index == 2 else
                    -self.radius_true if child.index == 3 else 0
                )
                .rotate90('y' if child.index in (2, 3) else 'y')
                .translate(
                    "x",
                    self.vertical_propulsor_loc*self.envelope_radius if child.index in (0,1) else 0
                )
                .translate(
                    "x",
                    self.vertical_propulsor_loc*self.envelope_radius if child.index in (2, 3) else 0
                )
            )
        )

    @Attribute
    def shape(self):
        shapes = [p.shape for p in self.propulsors]
        return Fused(shape_in=shapes[0], tool=shapes[1:])


if __name__ == '__main__':
    from parapy.gui import display
    from parapy.geom import Position

    prop_system = VerticalPropulsion(
        radius=1.0,
        envelope_radius=0.5,
        strut_size=0.1,
        position=Position(),
        vertical_num_blades=3,
        c_tip=0.08,
        sweep_TE=5.0,
        airfoil_file='whitcomb.dat',
        blade_data_file_vertical='blade_data_vertical.xlsx',
        label='verticalpropulsion'
    )
    display(prop_system)