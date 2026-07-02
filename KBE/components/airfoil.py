#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 ParaPy Holding B.V.
#
# This file is subject to the terms and conditions defined in
# the license agreement that you have received with this source code
#
# THIS CODE AND INFORMATION ARE PROVIDED "AS IS" WITHOUT WARRANTY OF ANY
# KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR
# PURPOSE.

import os.path
from parapy.geom import FittedCurve
from parapy.core import Input, Attribute
from primiplane import AIRFOIL_DIR


class Airfoil(FittedCurve):  # note the use of FittedCurve as superclass
    chord: float = Input(1.)
    airfoil_name: str = Input()
    thickness_factor: float = Input(1.)

    mesh_deflection: float = Input(1e-4)
    tolerance: float = Input(1e-4)

    @Attribute
    def points(self):  # required slot for FittedCurve superclass
        if self.airfoil_name.endswith('.dat'):  # check whether the airfoil name string includes .dat already
            airfoil_file = self.airfoil_name
        else:
            airfoil_file = self.airfoil_name + '.dat'
        file_path = os.path.join(AIRFOIL_DIR, airfoil_file)
        with open(file_path, 'r') as f:
            point_lst = []
            for line in f:
                x, z = line.split(' ', 1)  # the cartesian coordinates are directly interpreted as X and Z coordinates
                point_lst.append(self.position.translate(
                    "x", float(x) * self.chord,  # the x points are scaled according to the airfoil chord length
                    "z", float(z) * self.chord * self.thickness_factor)) # y points are scaled according to thickness factor
        return point_lst


if __name__ == '__main__':
    from parapy.gui import display

    foil = Airfoil(label="airfoil", airfoil_name='whitcomb')
    display(foil)
