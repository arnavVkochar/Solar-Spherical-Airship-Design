from parapy.core import Base, Input, Part, action, Attribute
import env_Arnesh as env
from components.envelope import Envelope
from components.payload import Payload
from components.battery import Battery
from components.solar import SolarPanel
from components.vertical_propulsion import VerticalPropulsion
from components.horizontal_propulsion import HorizontalPropulsion
from components.vertical_prop_strut import StrutSupport
from components.horizontal_prop_strut import StrutSupportH
from components.payloadsupports import PayloadSupports
import matlab.engine
import sys
from components.ballonet import Ballonet
import warnings
import subprocess
from parapy.exchange import STEPWriter
from parapy.core.validate import GreaterThan, LessThan
from Optimizer.Optim_modules.envelope_buoyancy_module import run_model as compute_buoyancy

from assembly.mission_analysis import MissionAnalysis
from PrelimSizing.kb_prop_radius import size_prop_radius
import os

DIR = os.path.dirname(os.path.abspath(__file__))   
PARENT_DIR = os.path.dirname(DIR)                 
PROP_EXCEL_PATH = os.path.join(PARENT_DIR, "prop_Ct_Cp_vs_J.xlsx")
from Helper_Scripts.Output_XML import write_flight_gear_xml
from Helper_Scripts.Output_XML import write_prop_xml
from Helper_Scripts.convert_step_to_ac3d import run_freecad_conversion, run_blender_conversion
from Helper_Scripts.Output_pdf import write_pdf

def generate_warning(warning_header, msg):
    from tkinter import Tk, messagebox
    window = Tk()
    window.withdraw()
    messagebox.showwarning(warning_header, msg)
    window.deiconify()
    window.destroy()
    window.quit()

class Airship(Base):
    simulation_timestep_s = Input(1200)
    envelope_radius = Input(10.0)
    envelope_thickness = Input(0.1) #does not alter mass as mass is calculated from mass per m2 - only used for geo building and offsets
    envelope_mass_per_m2 = Input(5)

    ballonet_radius = Input(5.0)
    ballonet_thickness = Input(0.1)#same as envelope radius
    ballonet_mass_per_m2 = Input(5)

    lifting_gas_density_sl = Input(0.0899)
    ambient_gas_density_sl = Input(1.225)

    cruise_altitude_m = Input(6000)
    ceiling_tolerance_m = Input(500)

    energy_per_panel_J = Input(0)
    solar_panel_eta= Input(0.33)
    solar_area_per_panel = Input(10.0)
    required_solar_area = Input(40.0)
    solar_panel_weight_per_panel = Input(2)


    #dry_gas_mass = Input(400)

    #ambient_gas_mass = Input(100)

    payload_load_patch_radius = Input(0.5)
    payload_load_patch_loc = Input(0.7)

    payload_length= Input(4.0)
    payload_width= Input(2.0)
    payload_height= Input(2.0)
    payload_d_factor= Input(1.15)
    payload_weight = Input(200)

    battery_length =Input(2.0)
    battery_width= Input(1.5)
    battery_height= Input(1.5)
    battery_weight_per_unit_volume = Input(1.5)
    number_of_batteries = Input(2)

    energy_per_battery = Input(120000.0)

    vertical_prop_radius= Input(1.0)
    horizontal_prop_radius = Input(1.0) #used for propeller radius breaking circular dependency needs to be updated to correct weight
    strut_size= Input(1.4)
    #strut_size_h = Input(1.4)
    strut_radius= Input(0.05)
    strut_radius_h = Input(0.05)

    vertical_num_blades= Input(3)
    horizontal_num_blades = Input(3)
    sweep_TE= Input(0.0)
    airfoil_file= Input('whitcomb.dat')
    blade_data_file_vertical= Input('blade_data_vertical.xlsx')
    blade_data_file_horizontal = Input('blade_data_output2.xlsx')
    vertical_propulsor_loc = Input(0)
    horizontal_propulsor_loc = Input(0)

    wind_speed= Input(0.0)
    wind_direction= Input(0.0)
    wind_vertical_component= Input(0.0)
    #design_airspeed= Input(10.0)
    #hub_to_tip_ratio_h = Input(0.2,doc="Horizontal propeller hub-to-tip ratio [-]")

    hub_to_tip_h = Input(0.2)
    hub_to_tip_v = Input(0.2)
    max_rpm = Input(4000)
    start_year = Input()
    start_month = Input()
    start_date = Input()
    start_hour = Input()
    start_minute = Input()
    max_airspeed_ms = Input(8)

    @Attribute
    def effective_envelope_radius(self):
        return self.envelope.effective_radius

    @Attribute
    def _computed_horizontal_prop_radius(self):
        drag_force = self.envelope.drag_at_max_airspeed
        thrust_per_prop = drag_force / 2

        prop_result = size_prop_radius(
            thrust_required_N=thrust_per_prop,
            blade_data_file=os.path.join(PARENT_DIR, "blade_data_output2.xlsx"),
            env_basepath=env.basepath,
            num_blades=self.horizontal_num_blades,
            hub_to_tip=self.hub_to_tip_h,
            design_airspeed=self.max_airspeed_ms,
            max_rpm=self.max_rpm,
            c_tip_fraction=1,
        )
        return prop_result["prop_radius_m"]


    @Attribute
    def effective_strut_size(self):#ensures that struts does not interfere with the blade radius
        min_size = 2 * self.vertical_prop_radius
        if self.strut_size < min_size:
            msg = (f"Strut_size ({self.strut_size} m) is less than 2 * vertical_prop_radius. Blade passing through struts "
                   f"({min_size} m). Value will be set to {min_size} m.")
            generate_warning("Warning: Strut Size Overridden", msg)
            return min_size
        return self.strut_size

    @Attribute
    def effective_strut_size_h(self):
        min_size = 2 * self._computed_horizontal_prop_radius
        return min_size



    @Part
    def envelope(self):
        return Envelope(
            radius=self.auto_envelope_radius,
            ballonet_radius = self.ballonet_radius,
            thickness=self.envelope_thickness,
            epm2=self.envelope_mass_per_m2,
            #dgm = self.dry_gas_mass, It will be calculated
            req_solar_area = self.required_solar_area,
            area_per_panel = self.solar_area_per_panel,
            gas_density_sl = self.lifting_gas_density_sl,
            #dry_mass = self.structural_mass,
            #ballonet_mass_per_m2=self.ballonet_mass_per_m2,
            ballonet_thickness =self.ballonet_thickness,
            cruise_altitude_m=self.cruise_altitude_m,
            max_airspeed_ms=self.max_airspeed_ms,
        )

    @Part
    def ballonet(self):
        return Ballonet(
            radius=self.ballonet_radius,
            thickness=self.ballonet_thickness,
            bpm2=self.ballonet_mass_per_m2,
            #dgmair=self.ambient_gas_mass, Being calculated now
            envelope_radius=self.effective_envelope_radius,
            envelope_thickness=self.envelope_thickness,
            ambient_gas_density_sl = self.ambient_gas_density_sl
        )

    @Part
    def payload(self):
        return Payload(
            envelope_radius=self.effective_envelope_radius,
            length=self.payload_length,
            width=self.payload_width,
            height=self.payload_height,
            payload_d_factor=self.payload_d_factor,
            pweight=self.payload_weight,
        )

    @Part
    def payloadsupports(self):
        return PayloadSupports(
            envelope_radius=self.effective_envelope_radius,
            envelope_thickness=self.envelope_thickness,
            payload_load_patch_radius=self.payload_load_patch_radius,
            payload_load_patch_loc=self.payload_load_patch_loc
        )

    @Part
    def battery(self):
        return Battery(
            length=self.battery_length,
            width=self.battery_width,
            height=self.battery_height,
            position=self.payload.shape.position.translate(
                "z", -(self.payload_height / 2 + self.battery_height / 2)),
            bwpuv=self.battery_weight_per_unit_volume,
            nob = self.number_of_batteries
                        )

    @Part
    def solar_panel(self):
        return SolarPanel(
            solar_panel_eta=self.solar_panel_eta,
            area_per_panel=self.solar_area_per_panel,
            req_area=self.required_solar_area,
            envelope_radius=self.effective_envelope_radius,
            sweight = self.solar_panel_weight_per_panel
        )

    @Part
    def vertical_propulsion(self):
        return VerticalPropulsion(
            radius=self.vertical_prop_radius,
            envelope_radius=self.effective_envelope_radius,
            position=self.envelope.shape.position,
            strut_size=self.strut_size,
            vertical_num_blades=self.vertical_num_blades,
            sweep_TE=self.sweep_TE,
            airfoil_file=self.airfoil_file,
            blade_data_file_vertical=self.blade_data_file_vertical,
            vertical_propulsor_loc=self.vertical_propulsor_loc,
            hub_to_tip_v=self.hub_to_tip_v,
            # vertical_prop_weight=self.vertical_prop_weight,
        )
    """
    @Attribute
    def size_prop_radius_h(self):
        thrust_per_prop = self.envelope.drag_at_max_airspeed / 2

        prop_result = size_prop_radius(
            thrust_required_N=thrust_per_prop,  # drag / 2 from envelope_drag
            blade_data_file=os.path.join(os.path.dirname(__file__), "blade_data_output2.xlsx"),
            env_basepath=env.basepath,
            num_blades=self.horizontal_num_blades,
            hub_to_tip=self.hub_to_tip_h,
            design_airspeed=self.max_airspeed_ms,  # worst-case from kb_max_airspeed
            max_rpm=7000.0,
        )
        prop_radius = prop_result["prop_radius_m"]
        return prop_radius
    """

    @Part
    def horizontal_propulsion(self):
        return HorizontalPropulsion(
            design_airspeed=self.max_airspeed_ms,
            radius=self._computed_horizontal_prop_radius,
            weight_radius=self.horizontal_prop_radius, #therefore, input needs to match the radius given by auto calc, which will update everything slightly again if altitude is again infeasible
            envelope_radius=self.effective_envelope_radius,
            position=self.envelope.shape.position,
            strut_size=self.effective_strut_size_h,
            horizontal_num_blades=self.horizontal_num_blades,
            sweep_TE=self.sweep_TE,
            c_tip = self._computed_horizontal_prop_radius,
            airfoil_file=self.airfoil_file,
            blade_data_file_horizontal=os.path.join(PARENT_DIR, "blade_data_output2.xlsx"),
            horizontal_propulsor_loc=self.horizontal_propulsor_loc,
            hub_to_tip_h=self.hub_to_tip_h,
        )

    @Part
    def vertical_prop_strut(self):
        return StrutSupport(
            envelope_thickness=self.envelope_thickness,
            envelope_radius=self.effective_envelope_radius,
            position=self.envelope.shape.position,
            strut_size=self.effective_strut_size,
            strut_radius=self.strut_radius,
            vertical_propulsor_loc=self.vertical_propulsor_loc,
        )

    @Part
    def horizontal_prop_strut(self):
        return StrutSupportH(
            envelope_radius=self.effective_envelope_radius,
            envelope_thickness=self.envelope_thickness,
            position=self.envelope.shape.position,
            strut_size=self.effective_strut_size_h,
            strut_radius=self.strut_radius_h,
            horizontal_propulsor_loc=self.horizontal_propulsor_loc,
        )

    @Attribute
    def airship_solid_components(self):
        def as_list(s):
            return s if isinstance(s, (list, tuple)) else [s]

        return [
            self.envelope.shape,
            self.payload.shape,
            self.battery.shape,
            self.solar_panel.shape,
            *as_list(self.vertical_propulsion.shape),
            *as_list(self.horizontal_propulsion.shape),
            *as_list(self.vertical_prop_strut.shape),
            *as_list(self.horizontal_prop_strut.shape),
        ]

    @Part
    def step_writer_components(self):
        return STEPWriter(
            default_directory=DIR,
            filename="airship_components.stp",
            trees=self.airship_solid_components,
            hidden=1
        )

    @action
    def write_step_components(self):
        self.step_writer_components.write()

    @action
    def write_ac3d(self):
        step_file = os.path.join(PARENT_DIR, "airship_components.stp")
        intermediate_file = os.path.join(PARENT_DIR, "airship_components.stl")
        ac_file = os.path.join(PARENT_DIR, "Airship", "Models", "airship_components.ac")

        self.write_step_components()

        run_freecad_conversion(step_file, intermediate_file)
        run_blender_conversion(intermediate_file, ac_file)

    @action
    def write_xml(self):
        write_flight_gear_xml(self)
        write_prop_xml(xlsx_path=PROP_EXCEL_PATH)

    @action
    def launch_flightgear(self):
        self.write_step_components()
        self.write_ac3d()
        self.write_xml()

        subprocess.Popen([
            env.flightgear_path,
            env.fg_KBE_path,
            "--aircraft=Airship",
            "--timeofday=noon",
            "--enable-terrasync",
            "--prop:/input/joysticks/enabled=false",
            "--wind=0@0",
            "--disable-real-weather-fetch"
        ])

    @action
    def write_pdf(self):
        write_pdf(self)

    @Attribute
    def structural_mass(self):
        print(f"Envelope weight:{self.envelope.weight:.2f} kg")
        print(f"Ballonet weight:{self.ballonet.weight:.2f} kg")
        print(f"Payload weight:{self.payload.weight:.2f} kg")
        print(f"Battery weight:{self.battery.weight:.2f} kg")
        print(f"Solar panel weight:{self.solar_panel.weight:.2f} kg")
        print(f"Horizontal propulsion weight:{2 * self.horizontal_propulsion.weight:.2f} kg")
        print(f"Vertical propulsion weight: {4 * self.vertical_propulsion.weight:.2f} kg")
        print(f"Total structural mass: {self.envelope.weight + self.ballonet.weight + self.payload.weight + self.battery.weight + self.solar_panel.weight + 2 * self.horizontal_propulsion.weight + 4 * self.vertical_propulsion.weight:.2f} kg")
        return (
                self.envelope.weight +
                self.ballonet.weight +
                self.payload.weight +
                self.battery.weight +
                self.solar_panel.weight +
                2 * self.horizontal_propulsion.weight +
                4 * self.vertical_propulsion.weight
                #self.horizontal_prop_strut.weight+
                #self.vertical_prop_strut.weight
                #strut weights, COG and inertia not modelled as of this version
        )

    @Attribute
    def total_mass(self):
        print(f"Lifting gas weight: {self.envelope.gas_mass} kg")
        print(f"Ballonet gas weight: {self.ballonet.gas_mass} kg")
        return self.structural_mass + self.envelope.gas_mass + self.ballonet.gas_mass

    @Attribute
    def cog(self):
        from parapy.geom import Point
        components = [
            (self.envelope.weight, self.envelope.cog),
            (self.solar_panel.weight, self.solar_panel.cog),
            (self.ballonet.weight, self.ballonet.cog),
            (self.payload.weight, self.payload.cog),
            (self.battery.weight, self.battery.cog)
            #(self.horizontal_prop_strut.weight, self.horizontal_prop_strut.cog),
            #(self.vertical_prop_strut.weight, self.vertical_prop_strut.cog)

        ]
        total = sum(w for w, _ in components)
        x = sum(w * p.x for w, p in components) / total
        y = sum(w * p.y for w, p in components) / total
        z = sum(w * p.z for w, p in components) / total
        return Point(x, y, z)

    @Attribute
    def inertia_tensor(self):
        scg = self.cog

        def shift(comp_cog, comp_weight, comp_inertia):
            dx = comp_cog.x - scg.x
            dy = comp_cog.y - scg.y
            dz = comp_cog.z - scg.z
            Ixx = comp_inertia.get("Ixx", 0.0) + comp_weight * (dy ** 2 + dz ** 2)
            Iyy = comp_inertia.get("Iyy", 0.0) + comp_weight * (dx ** 2 + dz ** 2)
            Izz = comp_inertia.get("Izz", 0.0) + comp_weight * (dx ** 2 + dy ** 2)
            Ixy = comp_inertia.get("Ixy", 0.0) + comp_weight * dx * dy
            Ixz = comp_inertia.get("Ixz", 0.0) + comp_weight * dx * dz
            Iyz = comp_inertia.get("Iyz", 0.0) + comp_weight * dy * dz
            return {
                "Ixx": Ixx, "Iyy": Iyy, "Izz": Izz,
                "Ixy": Ixy, "Ixz": Ixz, "Iyz": Iyz,
            }

        contributions = [
            shift(self.envelope.cog,
                self.envelope.weight,
                self.envelope.inertia),
            shift(self.ballonet.cog,
                self.ballonet.weight,
                self.ballonet.inertia),
            shift(self.payload.cog,
                self.payload.weight,
                self.payload.inertia),
            shift(self.battery.cog,
                self.battery.weight,
                self.battery.inertia),
            shift(self.solar_panel.cog,
                self.solar_panel.weight,
                self.solar_panel.inertia)
            #shift(self.horizontal_prop_strut.cog,
            #  self.horizontal_prop_strut.weight,
            # self.horizontal_prop_strut.inertia),
            #shift(self.vertical_prop_strut.cog,
            # self.vertical_prop_strut.weight,
            #self.vertical_prop_strut.inertia),
        ]

        return {
            "Ixx": sum(c["Ixx"] for c in contributions),
            "Iyy": sum(c["Iyy"] for c in contributions),
            "Izz": sum(c["Izz"] for c in contributions),
            "Ixy": sum(c["Ixy"] for c in contributions),
            "Ixz": sum(c["Ixz"] for c in contributions),
            "Iyz": sum(c["Iyz"] for c in contributions),
        }

    @Attribute
    def _buoyancy_results(self):#calc buoyancy based on initial envelope radius given by user
        import math

        V_ballonet = (4.0 / 3.0) * math.pi * self.ballonet_radius ** 3
        V_envelope = (4.0 / 3.0) * math.pi * self.envelope_radius ** 3
        ballonet_vf_sl = V_ballonet / V_envelope

        from Optimizer.Optim_modules.propeller_weight import run_model as compute_prop_weight
        _h_prop_weight_estimate = compute_prop_weight({
            "excel_path": os.path.join(PARENT_DIR, self.blade_data_file_horizontal),
            "prop_radius_m": self.horizontal_prop_radius,
            "blade_count": self.horizontal_num_blades,
            "hub_to_tip": self.hub_to_tip_h,
        })["total_assembly_weight_kg"]

        dry_mass = (
                self.payload.weight +
                self.battery.weight +
                self.solar_panel.weight +
                2 * _h_prop_weight_estimate +
                4 * self.vertical_propulsion.weight
        )

        return compute_buoyancy({
            "mode": "constraint",
            "radius": self.envelope_radius,
            "ballonet_volume_fraction_sl": ballonet_vf_sl,
            "gas_density_sl": self.lifting_gas_density_sl,
            "dry_mass": dry_mass,
            "envelope_mass_per_m2": self.envelope_mass_per_m2,
            "envelope_thickness": self.envelope_thickness,
            "ballonet_mass_per_m2": self.ballonet_mass_per_m2,
            "ballonet_thickness": self.ballonet_thickness,
            "ceiling_tolerance_m": self.ceiling_tolerance_m,
            "cruise_altitude_m": self.cruise_altitude_m,
        })

    @Part
    def mission_analysis(self):
        return MissionAnalysis()
    
    @Attribute
    def _excel_params(self):

        return {
            "start_year": self.start_year,
            "start_month":self.start_month,
            "start_day": self.start_date,
            "start_hour":self.start_hour,
            "start_minute":self.start_minute,
        }
    
    @Attribute
    def auto_envelope_radius(self):#although kind of redundant, a separate function apart from the prelim envelope sizing is needed as that estimates dry mass
        from assembly.mission_analysis import _find_min_radius
        result = self._buoyancy_results
        if result["achievable_altitude_m"] >= self.cruise_altitude_m:
            return self.envelope_radius   #input can be used directly

        #Input cannot be used as it is infeasible for mission
        min_r = _find_min_radius(self, self.cruise_altitude_m)
        msg = (
            f"Payload/config change made radius {self.envelope_radius:.2f} m infeasible.\n"
            f"Auto-resizing envelope to {min_r:.2f} m to reach {self.cruise_altitude_m} m."
        )
        generate_warning("Auto Resize: Envelope Radius Updated", msg)
        return min_r


    @Attribute
    def _buoyancy_results_effective(self):
        import math
        from Optimizer.Optim_modules.propeller_weight import run_model as compute_prop_weight

        r = self.auto_envelope_radius
        V_ballonet = (4.0 / 3.0) * math.pi * self.ballonet_radius ** 3
        ballonet_vf_sl = V_ballonet / ((4.0 / 3.0) * math.pi * r ** 3)

        _h_prop_weight_estimate = compute_prop_weight({
            "excel_path": self.blade_data_file_horizontal,
            "prop_radius_m": self.horizontal_prop_radius,
            "blade_count": self.horizontal_num_blades,
            "hub_to_tip": self.hub_to_tip_h,
        })["total_assembly_weight_kg"]

        dry_mass = (
                self.payload.weight +
                self.battery.weight +
                self.solar_panel.weight +
                2 * _h_prop_weight_estimate +
                4 * self.vertical_propulsion.weight
        )

        return compute_buoyancy({
            "mode": "constraint",
            "radius": r,
            "ballonet_volume_fraction_sl": ballonet_vf_sl,
            "gas_density_sl": self.lifting_gas_density_sl,
            "dry_mass": dry_mass,
            "envelope_mass_per_m2": self.envelope_mass_per_m2,
            "envelope_thickness": self.envelope_thickness,
            "ballonet_mass_per_m2": self.ballonet_mass_per_m2,
            "ballonet_thickness": self.ballonet_thickness,
            "ceiling_tolerance_m": self.ceiling_tolerance_m,
            "cruise_altitude_m": self.cruise_altitude_m,
        })