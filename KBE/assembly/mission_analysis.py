"""
This is our mission feasibility module. This section of the code performs two main tasksL:

1. Altitude feasibility analysis – checks if the airship can reach the required cruise altitude.
2. Energy feasibility analysis – checks whether the solar panels can support the mission.
"""


from parapy.core import Base, Attribute, action
import env_Arnesh as env
import matlab.engine
import sys
from components.ballonet import Ballonet
import os
DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(DIR)
from Optimizer.Optim_modules.envelope_buoyancy_module import run_model as compute_buoyancy

import warnings
import math
import pandas as pd
from datetime import datetime

# Function to create a popup warning window.
def generate_warning(warning_header, msg):
        from tkinter import Tk, messagebox
        window = Tk()
        window.withdraw()
        messagebox.showwarning(warning_header, msg)
        window.deiconify()
        window.destroy()
        window.quit()


#Finds the minimum envelope radius required to reach a target altitude and uses binary search.
def _find_min_radius(parent, target_alt_m, r_lo=5.0, r_hi=100.0, tol=0.1):
    dry_mass = (
        #Calculates total mass excluding lifting gas
        parent.payload.weight + #parent is the Airship object containing all design data.
        parent.battery.weight +
        parent.solar_panel.weight +
        2 * parent.horizontal_propulsion.weight +
        4 * parent.vertical_propulsion.weight
    ) #again, strut weights are not including in dry mass in this version

    V_ballonet = (4.0 / 3.0) * math.pi * parent.ballonet_radius ** 3

    base_params = {
        #Stores parameters that do not change during binary search and this was done to avoid rebuilding them every iteration.
        "mode":"constraint",
        "gas_density_sl":parent.lifting_gas_density_sl,
        "dry_mass":dry_mass,
        "envelope_mass_per_m2": parent.envelope_mass_per_m2,
        "envelope_thickness": parent.envelope_thickness,
        "ballonet_mass_per_m2": parent.ballonet_mass_per_m2,
        "ballonet_thickness": parent.ballonet_thickness,
        "ceiling_tolerance_m": parent.ceiling_tolerance_m,
        "cruise_altitude_m":target_alt_m,
    }

    for _ in range(60):
        r_mid = (r_lo + r_hi) / 2.0
        ballonet_vf_sl = V_ballonet / ((4.0 / 3.0) * math.pi * r_mid ** 3)
        result = compute_buoyancy({
            **base_params,
            "radius":r_mid,
            "ballonet_volume_fraction_sl": ballonet_vf_sl,
        })
        if result["achievable_altitude_m"] >= target_alt_m:
            r_hi = r_mid
        else:
            r_lo = r_mid
        if (r_hi - r_lo) < tol:
            break
    return r_hi

# This is the main class responsible for mission feasibility evaluation.
class MissionAnalysis(Base):
    @Attribute
    def _excel_params(self):
        #Reads mission start date and time from Excel.
        import pandas as pd
        from datetime import datetime

        df = pd.read_excel(env.excel_file_path, engine="openpyxl",sheet_name='KBE_Input')
        data = {
            str(row["Parameter"]).strip(): row["Value"]
            for _, row in df.iterrows()
            if pd.notna(row["Value"])
        }

        start_datetime_raw = data.get('Start Date')
        start_time_raw = str(data.get('Start Time (CET)')).strip().split()[0]
        start_dt = datetime.strptime(
            f"{str(start_datetime_raw).split(' ')[0]} {start_time_raw}",
            "%Y-%m-%d %H:%M"
        )

        return {
            "start_year": start_dt.year,
            "start_month":start_dt.month,
            "start_day":start_dt.day,
            "start_hour":start_dt.hour,
            "start_minute": start_dt.minute,
        }


    @Attribute
    def achievable_altitude_m(self):
        #this will returns maximum altitude the design can reach
        return self.parent._buoyancy_results_effective["achievable_altitude_m"]

    @Attribute
    def cruise_altitude_m(self):
        #this will returns cruise altitude that the design HAS to reach
        return self.parent.cruise_altitude_m

    @Attribute
    def altitude_margin_m(self):

        return self.achievable_altitude_m - self.cruise_altitude_m

    @Attribute
    def altitude_feasible(self):
        #returns True if achievable altitude exceeds cruise altitude, and if false, finds required radius
        feasible = self.altitude_margin_m >= 0
        if not feasible:
            min_radius = _find_min_radius(self.parent, self.cruise_altitude_m)
            msg = (
                f"Altitude infeasible: current envelope radius "
                f"{self.parent.effective_envelope_radius:.2f} m can only reach "
                f"{self.achievable_altitude_m:.0f} m — "
                f"{abs(self.altitude_margin_m):.0f} m below the target of "
                f"{self.cruise_altitude_m:.0f} m.\n\n"
                f"Minimum required envelope radius: {min_radius:.2f} m\n"
                f"(estimated with all other parameters held constant)"
            )
            warnings.warn(msg)
            generate_warning("Warning: Altitude Margin Negative", msg)
        return feasible

    """
    @Attribute
    def _energy_simulation(self):
        #This will run the full MATLAB mission simulation using actual airship parameters.
        bvf_sl = self.parent.ballonet.ballonet_volume_fraction_sl

        eng3 = matlab.engine.start_matlab()
        python_exe = sys.executable.replace('\\', '/')
        eng3.eval(f"pyenv('Version', '{python_exe}');", nargout=0)
        sim_path = os.path.join(PARENT_DIR, "Optimizer")
        eng3.addpath(eng3.genpath(sim_path), nargout=0)
        eng3.addpath(PARENT_DIR, nargout=0)
        perf = self.parent.horizontal_propulsion._performance_data
        design_params = {
            "rpm_arr": matlab.double(perf["rpm"]),
            "thrust_arr": matlab.double(perf["thrust"]),
            "eta_arr": matlab.double(perf["eta"]),
            "envelope_radius": self.parent.effective_envelope_radius,
            "num_panels": round(
                self.parent.required_solar_area /
                self.parent.solar_area_per_panel),
            "solar_area_per_panel": self.parent.solar_area_per_panel,
            "energy_per_panel_J": self.parent.energy_per_panel_J,
            "solar_panel_eta": self.parent.solar_panel_eta,
            "num_battery": self.parent.number_of_batteries,
            "prop_radius_h": self.parent._computed_horizontal_prop_radius,
            "prop_weight_h": self.parent.horizontal_propulsion.weight,
            "prop_weight_v": self.parent.vertical_propulsion.weight,
            "prop_radius_v": self.parent.vertical_prop_radius,
            "hub_to_tip_ratio_h": self.parent.hub_to_tip_h,
            "hub_to_tip_ratio_v": self.parent.hub_to_tip_v,
            "blade_count_h": self.parent.horizontal_num_blades,
            "blade_count_v": self.parent.vertical_num_blades,
            "ballonet_volume_fraction_sl": bvf_sl,
            "payload_weight": self.parent.payload_weight,
            "payload_length": self.parent.payload_length,
            "payload_width": self.parent.payload_width,
            "payload_height": self.parent.payload_height,
            "payload_d_factor": self.parent.payload_d_factor,
            "cruise_altitude_m": self.parent.cruise_altitude_m,
            "envelope_thickness": self.parent.envelope_thickness,
            "envelope_mass_per_m2": self.parent.envelope_mass_per_m2,
            "ballonet_thickness": self.parent.ballonet_thickness,
            "ballonet_mass_per_m2": self.parent.ballonet_mass_per_m2,
            "gas_density": self.parent.lifting_gas_density_sl,
            "solar_panel_weight_per_panel": self.parent.solar_panel_weight_per_panel,
            "battery_length": self.parent.battery_length,
            "battery_width": self.parent.battery_width,
            "battery_height": self.parent.battery_height,
            "battery_weight_per_unit_volume": self.parent.battery_weight_per_unit_volume,
            "energy_per_battery": self.parent.energy_per_battery,
            "optim_modules_path": env.optim_modules_path,
            "mission_plan_path": env.mission_plan_file_path,
            "blade_data_path": env.blade_data_path,
            "start_year": self.parent.start_year,
            "start_month": self.parent.start_month,
            "start_date": self.parent.start_date,
            "start_hour": self.parent.start_hour,
            "start_minute": self.parent.start_minute,
        }

        eng3.run_mission_simulation(design_params, nargout=0)
        total_energy_J = eng3.workspace["energygentotal"]
        total_energy_consumed = eng3.workspace["energycontotal"]
        solar_panels_enough = eng3.workspace["solar_panels_enough"]
        propeller_thrust_enough = eng3.workspace["propeller_thrust_enough"]

        eng3.quit()
        return {
            "total_energy_J": total_energy_J,
            "total_energy_Wh": total_energy_J / 3600,
            "total_energy_kWh": total_energy_J / 3600000,
            "total_energy_consumed": total_energy_consumed,
            "solar_panels_enough": solar_panels_enough,
            "propeller_thrust_enough": propeller_thrust_enough,
        }
        """
    @Attribute
    def _energy_simulation_gen(self):
        #This runs a simplified energy generation simulation. Envelope and buoyancy effects do not have to be taken into account
        bvf_sl = 0.1

        eng3 = matlab.engine.start_matlab()
        python_exe = sys.executable.replace('\\', '/')
        eng3.eval(f"pyenv('Version', '{python_exe}');", nargout=0)
        sim_path = os.path.join(PARENT_DIR, "Optimizer")
        eng3.addpath(eng3.genpath(sim_path), nargout=0)
        eng3.addpath(PARENT_DIR, nargout=0)
        perf = self.parent.horizontal_propulsion._performance_data
        design_params = {
            "rpm_arr": matlab.double(perf["rpm"]),
            "thrust_arr": matlab.double(perf["thrust"]),
            "eta_arr": matlab.double(perf["eta"]),
            "envelope_radius": self.parent.effective_envelope_radius,
            "num_panels": round(
                self.parent.required_solar_area /
                self.parent.solar_area_per_panel),
            "solar_area_per_panel": self.parent.solar_area_per_panel,
            "energy_per_panel_J": self.parent.energy_per_panel_J,
            "solar_panel_eta": self.parent.solar_panel_eta,
            "num_battery": self.parent.number_of_batteries,
            "prop_radius_h": self.parent._computed_horizontal_prop_radius,
            "prop_weight_h": self.parent.horizontal_propulsion.weight,
            "prop_weight_v": self.parent.vertical_propulsion.weight,
            "prop_radius_v": self.parent.vertical_prop_radius,
            "hub_to_tip_ratio_h": self.parent.hub_to_tip_h,
            "hub_to_tip_ratio_v": self.parent.hub_to_tip_v,
            "blade_count_h": self.parent.horizontal_num_blades,
            "blade_count_v": self.parent.vertical_num_blades,
            "ballonet_volume_fraction_sl": bvf_sl,
            "payload_weight": self.parent.payload_weight,
            "payload_length": self.parent.payload_length,
            "payload_width": self.parent.payload_width,
            "payload_height": self.parent.payload_height,
            "payload_d_factor": self.parent.payload_d_factor,
            "cruise_altitude_m":self.parent.cruise_altitude_m,
            "envelope_thickness": 0,
            "envelope_mass_per_m2": 0,
            "ballonet_thickness": 0,
            "ballonet_mass_per_m2": 0,
            "gas_density": 0,
            "solar_panel_weight_per_panel": self.parent.solar_panel_weight_per_panel,
            "battery_length": self.parent.battery_length,
            "battery_width": self.parent.battery_width,
            "battery_height": self.parent.battery_height,
            "battery_weight_per_unit_volume": self.parent.battery_weight_per_unit_volume,
            "energy_per_battery": self.parent.energy_per_battery,
            "optim_modules_path": env.optim_modules_path,
            "mission_plan_path": env.mission_plan_file_path,
            "blade_data_path": env.blade_data_path,
            "start_year": self.parent.start_year,
            "start_month": self.parent.start_month,
            "start_date": self.parent.start_date,
            "start_hour": self.parent.start_hour,
            "start_minute": self.parent.start_minute,
        }

        eng3.run_mission_simulation(design_params, nargout=0)
        total_energy_J = eng3.workspace["energygentotal"]
        total_energy_consumed = eng3.workspace["energycontotal"]
        solar_panels_enough = eng3.workspace["solar_panels_enough"]
        propeller_thrust_enough = eng3.workspace["propeller_thrust_enough"]

        eng3.quit()
        return {
            "total_energy_J": total_energy_J,
            "total_energy_Wh": total_energy_J / 3600,
            "total_energy_kWh": total_energy_J / 3600000,
            "total_energy_consumed": total_energy_consumed,
            "solar_panels_enough": solar_panels_enough,
            "propeller_thrust_enough": propeller_thrust_enough,
        }


    #For convenience and ease of access for visualising values, these functions below were added.
    @Attribute
    def energy_generated_J(self):
        return self._energy_simulation_gen["total_energy_J"]

    @Attribute
    def energy_generated_Wh(self):
        return self._energy_simulation_gen["total_energy_Wh"]

    @Attribute
    def energy_generated_kWh(self):
        return self._energy_simulation_gen["total_energy_kWh"]

    @Attribute
    def energy_consumed_J(self):
        return self._energy_simulation_gen["total_energy_consumed"]

    @Attribute
    def solar_panels_enough(self):
        return self._energy_simulation_gen["solar_panels_enough"]

    @Attribute
    def propeller_thrust_enough(self):
        return self._energy_simulation_gen["propeller_thrust_enough"]

    @Attribute
    def summary(self):
        # Collects all feasibility results into one dictionary, again for convenience
        return {
            "altitude_feasible": self.altitude_feasible,
            "achievable_alt_m": self.achievable_altitude_m,
            "cruise_alt_m": self.cruise_altitude_m,
            "altitude_margin_m": self.altitude_margin_m,
            "energy_generated_J": self.energy_generated_J,
            "energy_generated_Wh": self.energy_generated_Wh,
            "energy_generated_kWh": self.energy_generated_kWh,
            "energy_consumed_J": self.energy_consumed_J,
            "solar_panels_enough": self.solar_panels_enough,
            "propeller_thrust_enough": self.propeller_thrust_enough,
        }
    
    @action
    def check_altitude_feasibility(self):

        _ = self.altitude_feasible

    @action
    def check_energy_system_feasibility(self):
        _ = self.energy_generated_J
        _ = self.energy_generated_Wh
        _ = self.energy_generated_kWh
        _ = self.energy_consumed_J
        _ = self.solar_panels_enough
        _ = self.propeller_thrust_enough

    @action
    def check_mission_feasibility(self):
        _ = self.summary