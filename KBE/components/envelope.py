'''
This class represents the main airship envelope. This will be responsible for:

1. Creating the envelope geometry.
2. Checking if the envelope is large enough to fit the required solar panels.
3. Calculating envelope mass.
4. Calculating lifting gas mass.
5. Calculating inertia.
6. Plotting drag performance

This is the main component in our project, and has been modelled completely
'''

from parapy.core import Base, Input, Part, Attribute, action
from parapy.geom import Sphere, SubtractedSolid
import warnings
import sys
import math
import matplotlib.pyplot as plt
import numpy as np

from Optimizer.Optim_modules.solar_panel_min_radius import run_model as compute_min_radius
from Optimizer.Optim_modules.envelope_drag import run_model as compute_drag

def generate_warning(warning_header, msg):
    from tkinter import Tk, messagebox
    window = Tk()
    window.withdraw()
    messagebox.showwarning(warning_header, msg)
    window.deiconify()
    window.destroy()
    window.quit()


class Envelope(Base):
    radius= Input(10.0)
    ballonet_radius = Input(2.0)
    thickness= Input(0.1)
    epm2= Input(0.15)
    req_solar_area = Input(50.0)
    area_per_panel= Input(0.5)
    popup_gui= Input(True)
    max_airspeed_ms = Input(0.0)
    gas_density_sl = Input(0.1786)
    ballonet_thickness = Input(3e-4)
    cruise_altitude_m = Input(10000.0)


    @Attribute
    def min_required_radius(self):
        result = compute_min_radius({
            "req_area": self.req_solar_area,
            "area_per_panel": self.area_per_panel,
        })
        return result["min_radius_m"]

    @Attribute
    def effective_radius(self):
        if self.radius < self.min_required_radius:
            corrected = self.min_required_radius * 1.25 #for some margin otherwise load patches and last solar panel ring collide. Factor needs to be adjusted for larger radiis
            msg = (f"Envelope radius {self.radius} m is too small to fit all "
                   f"solar panels above the equator. "
                   f"Radius will be set to minimum internally to: {corrected:.4f} m. Please change it in your input as well.")
            warnings.warn(msg)
            if self.popup_gui:
                generate_warning("Warning: Envelope Radius Overridden", msg)
            else:
                print(f"[DEBUG] popup_gui is False — skipping popup")
            return corrected
        return self.radius


    @Part
    def outer_sphere(self):
        return Sphere(
            radius=self.effective_radius,
            color='white',
            hidden=True
        )

    @Part
    def inner_sphere(self):
        return Sphere(
            radius=max(self.effective_radius - self.thickness, 0.0),
            color='white',
            transparency=0.5,
            hidden=True
        )

    @Part
    def shape(self):
        return SubtractedSolid(
            shape_in=self.outer_sphere,
            tool=self.inner_sphere,
            color='white',
            transparency=0.0
        )

    @Attribute
    def weight(self):
        return 4 * math.pi * self.effective_radius**2 * self.epm2

    @Attribute
    def cog(self):
        return self.shape.position.point

    @Attribute
    def gas_mass(self):

        r_env= self.effective_radius
        t_env =self.thickness
        r_bal=self.ballonet_radius
        t_bal= self.ballonet_thickness

        v_envelope_total = (4.0 / 3.0) * math.pi * r_env ** 3 
        v_envelope_shell = 4.0 * math.pi * r_env ** 2 * t_env 
        v_interior = v_envelope_total - v_envelope_shell  

        v_ballonet = (4.0 / 3.0) * math.pi * r_bal ** 3  
        a_ballonet = 4.0 * math.pi * r_bal ** 2  
        v_ballonet_shell = a_ballonet * t_bal  
        v_usable = v_interior- v_ballonet_shell

        v_gas_sl = v_usable - v_ballonet  

        if v_gas_sl <= 0.0:
            raise ValueError(
                f"No space for lifting gas: V_gas_sl = {v_gas_sl:.3f} m³. "
                f"ballonet_radius ({r_bal} m) is too large relative to "
                f"envelope_radius ({r_env} m)."
            )

        return self.gas_density_sl * v_gas_sl

    @Attribute
    def inertia(self):
        r_o = self.effective_radius
        r_i = max(self.effective_radius - self.thickness, 0.0)
        I =(2/5) * self.weight * (r_o**5 - r_i**5) / (r_o**3 - r_i**3)
        I_gas = (2/5) * self.gas_mass * r_i**2
        return {"Ixx": I + I_gas, "Iyy": I + I_gas, "Izz": I + I_gas}

    @action
    def plot_drag_curve(self):
        airspeeds = np.linspace(0, self.max_airspeed_ms, 50)
        drag_forces = []
        cds = []

        for v in airspeeds:
            result = compute_drag({
                "envelope_radius": self.effective_radius,
                "airspeed": float(v),
                "cruise_altitude": self.cruise_altitude_m,
            })
            drag_forces.append(result["drag_force_N"])
            cds.append(result["cd"])

        altitudes = np.linspace(0, self.cruise_altitude_m + 1000, 50)
        drag_at_alt = []

        for alt in altitudes:
            result = compute_drag({
                "envelope_radius": self.effective_radius,
                "airspeed": float(self.max_airspeed_ms),
                "cruise_altitude": float(alt),
            })
            drag_at_alt.append(result["drag_force_N"])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
        fig.suptitle(
            f"Envelope drag  —  R = {self.effective_radius:.2f} m, "
            f"altitude = {self.cruise_altitude_m:.0f} m"
        )

        ax1.plot(airspeeds, drag_forces, color="steelblue")
        ax1.set_ylabel("Drag force [N]")
        ax1.set_xlabel("Airspeed [m/s]")
        ax1.grid(True, linestyle="--", alpha=0.5)

        ax2.plot(altitudes, drag_at_alt, color="tomato")
        ax2.set_ylabel("Drag force at max airspeed [N]")
        ax2.set_xlabel("Altitude [m]")
        ax2.set_title(f"Drag vs altitude at V = {self.max_airspeed_ms} m/s")
        ax2.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.show()

    @Attribute
    def drag_at_max_airspeed(self):
        result = compute_drag({
            "envelope_radius": self.effective_radius,
            "airspeed": self.max_airspeed_ms,
            "cruise_altitude": self.cruise_altitude_m,
        })
        return result["drag_force_N"]