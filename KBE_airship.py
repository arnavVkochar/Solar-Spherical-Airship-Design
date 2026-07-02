from parapy.core.validate import GreaterThan
from assembly.airship import Airship
from Helper_Scripts.import_inputs import *
from parapy.gui import display
import warnings
import pandas as pd
import sys
import env_Arnesh as env
import matlab.engine
import os
from datetime import datetime
from PrelimSizing.kb_envelope_radius import size_envelope_radius
from PrelimSizing.kb_envelope_radius import estimate_dry_mass
from PrelimSizing.kb_max_airspeed import find_max_airspeed
from PrelimSizing.kb_prop_radius import size_prop_radius

sys.path.insert(0, env.kbe_add_path)
from Optimizer.Optim_modules.envelope_drag import run_model
from Optimizer.Optim_modules.solar_panel_min_radius import _ring_layout, _all_panels_above_equator

import importlib
solar_mod = importlib.import_module('solar_power_generated')

import math

def max_panels_on_envelope(
    envelope_radius:float,
    area_per_panel:float,
    *,
    min_ring_fraction:float = 0.15,
    ring_spacing_factor:float = 1.0,
    azimuth_spacing_factor: float = 1.1,
):

    side = math.sqrt(area_per_panel)

    def _fits(n):
        rings = _ring_layout(
            envelope_radius, n, side,
            min_ring_fraction, ring_spacing_factor, azimuth_spacing_factor
        )
        return _all_panels_above_equator(rings)

    if not _fits(1):
        return {"max_panels": 0, "max_solar_area_m2": 0.0}

    lo, hi = 1, 2
    while _fits(hi):
        hi *= 2

    while (hi - lo) > 1:
        mid = (lo + hi) // 2
        if _fits(mid):
            lo = mid
        else:
            hi = mid

    max_n = lo
    rings = _ring_layout(
        envelope_radius, max_n, side,
        min_ring_fraction, ring_spacing_factor, azimuth_spacing_factor
    )

    return {
        "max_panels":max_n,
        "max_solar_area_m2": max_n * area_per_panel,
        "num_rings":len(rings),
        "last_ring_polar_deg": rings[-1]["polar_angle_deg"],
    }

filename = env.filename

warnings.filterwarnings("ignore", category=UserWarning,
                        message="Data Validation extension is not supported and will be removed")
df_init = pd.read_excel(filename, engine="openpyxl", sheet_name='KBE_Input')

data = {
    str(row["Parameter"]).strip(): row["Value"]
    for _, row in df_init.iterrows()
    if pd.notna(row["Value"])
}

user_type = str(data.get('Mode')).strip().lower()
print(user_type)


start_datetime_raw = data.get('Start Date')
start_time_raw = str(data.get('Start Time (CET)')).strip().split()[0]

start_dt = datetime.strptime(
    f"{str(start_datetime_raw).split(' ')[0]} {start_time_raw}", "%Y-%m-%d %H:%M"
)



if user_type == 'forward':
    obj = Airship(
        start_year=start_dt.year,
        start_month = start_dt.month,
        start_date = start_dt.day,
        start_hour = start_dt.hour,
        start_minute = start_dt.minute,

        solar_panel_eta = 0.33,

        envelope_radius=float(data.get('Outer Envelope Radius (m)')),
        envelope_thickness=float(data.get('Envelope Thickness (m)')),
        envelope_mass_per_m2 = float(data.get('Envelope Mass per m² (kg/m²)')),
        #dry_gas_mass = float(data.get('Gas Mass (kg)')),

        ballonet_radius=float(data.get('Ballonet Radius (m)')),
        ballonet_thickness=float(data.get('Ballonet Thickness (m)')),
        ballonet_mass_per_m2=float(data.get('Ballonet Mass per m² (kg/m²)')),
        #ambient_gas_mass=0.25,


        solar_area_per_panel=float(data.get('Solar Panel Area per Panel (m²)')),
        required_solar_area=float(data.get('Required Solar Panel Area (m²)')),
        solar_panel_weight_per_panel=float(data.get('Solar Panel Weight per Panel (kg)')),

        battery_length=float(data.get('Battery Length (m)')),
        battery_width=float(data.get('Battery Breadth (m)')),
        battery_height=float(data.get('Battery Height (m)')),
        #battery_specific_energy_density=float(data.get('Energy Capacity per Battery (J)')),
        battery_weight_per_unit_volume=float(data.get('Battery Weight per Unit Volume (kg/m³)')),
        number_of_batteries = int(data.get('Number of Batteries')),

        vertical_prop_radius=float(data.get('Vertical Propeller Radius (m)')),
        horizontal_prop_radius=float(data.get('Horizontal Propeller Radius (m)')),
        vertical_propulsor_loc=float(data.get('Vertical Propulsor Location (0–1)')),
        #vertical_prop_weight = float(data.get('Vertical Prop Weight (kg)')),

        #vertical_prop_weight=10,

        horizontal_propulsor_loc=float(data.get('Horizontal Propulsor Location (0–1)')),
        horizontal_num_blades=int(data.get('No. of Blades — Horizontal')),
        vertical_num_blades=int(data.get('No. of Blades — Vertical')),

        #horizontal_prop_weight=float(data.get('Horizontal Prop Weight (kg)')),

        #horizontal_prop_weight = 10,

        hub_to_tip_h=0.2,
        hub_to_tip_v=0.2,

        payload_load_patch_radius=float(data.get('Load-Patch Radius (m)')),
        payload_load_patch_loc=float(data.get('Load-Patch Location (0–1)')),
        payload_d_factor=float(data.get('Payload D Factor')),
        payload_weight=float(data.get('Payload Weight (kg)')),
        payload_length=float(data.get('Payload Length (m)')),
        payload_width=float(data.get('Payload Breadth (m)')),
        payload_height=float(data.get('Payload Height (m)')),

        strut_size=float(data.get('Vertical Strut Size (m)')),
        #strut_size_h=float(data.get('Horizontal Strut Size (m)')),
        strut_radius=float(data.get('Vertical Strut Radius (m)')),
        strut_radius_h=float(data.get('Horizontal Strut Radius (m)')),

        lifting_gas_density_sl = 0.0899,
        ambient_gas_density_sl = 1.225,
        cruise_altitude_m = float(data.get('Cruise Altitude (m)'))
    )
    display(obj)

elif user_type == 'inverse':
    optim_type = str(data.get('optim')).strip().lower()
    cruise_altitude_m = float(data.get('Cruise Altitude (m)'))
    envelope_thickness = float(data.get('Envelope Thickness (m)'))
    envelope_mass_per_m2 = float(data.get('Envelope Mass per m² (kg/m²)'))
    gas_density = float(data.get('Gas Density (kg/m³)'))
    ballonet_thickness = float(data.get('Ballonet Thickness (m)'))
    ballonet_mass_per_m2 = float(data.get('Ballonet Mass per m² (kg/m²)'))
    solar_area_per_panel = float(data.get('Solar Panel Area per Panel (m²)'))
    energy_per_battery = float(data.get('Energy Capacity per Battery (J)'))
    battery_weight_per_unit_volume = float(data.get('Battery Weight per Unit Volume (kg/m³)'))
    battery_length = float(data.get('Battery Length (m)'))
    battery_width = float(data.get('Battery Breadth (m)'))
    battery_height = float(data.get('Battery Height (m)'))
    payload_weight = float(data.get('Payload Weight (kg)'))
    payload_d_factor = float(data.get('Payload D Factor'))
    payload_length = float(data.get('Payload Length (m)'))
    payload_width = float(data.get('Payload Breadth (m)'))
    payload_height = float(data.get('Payload Height (m)'))
    load_patch_thickness = float(data.get('Load-Patch Thickness (m)'))
    load_patch_weight_per_volume = float(data.get('Load-Patch Weight per Unit Volume (kg/m³)'))
    solar_panel_weight_per_panel = float(data.get('Solar Panel Weight per Panel (kg)'))

    start_year = start_dt.year
    start_month = start_dt.month
    start_date = start_dt.day
    start_hour = start_dt.hour
    start_minute = start_dt.minute


    if optim_type =='prelim':
        print("prelim")
        #based on geometry given calculate
        #first based on cruise alt and ballonet fraction of 0.0044 calc radius
        battery_volume = battery_length * battery_width * battery_height
        battery_mass = battery_volume * battery_weight_per_unit_volume

        dm = estimate_dry_mass(
            payload_kg=payload_weight,
            n_batteries=4,
            battery_mass_kg=battery_mass,
            n_solar_panels=60,
            solar_panel_mass_kg=solar_panel_weight_per_panel,
        )
        kb = size_envelope_radius(
            cruise_altitude_m=cruise_altitude_m,
            dry_mass_kg=dm,
            gas_density_sl=gas_density,
            envelope_mass_per_m2=envelope_mass_per_m2,
            envelope_thickness=envelope_thickness,
            ballonet_mass_per_m2=ballonet_mass_per_m2,
            ballonet_thickness=ballonet_thickness,
            ballonet_volume_fraction_sl=0.0044,
        )
        radius = kb["radius_m"]
        print(radius)
        #calc highest airspeed and thus highest drag
        airspeed_result = find_max_airspeed(
            mission_plan_path=os.path.join(os.path.dirname(__file__), "mission_plan.xlsx"),
            start_year=start_dt.year,
            start_month=start_dt.month,
            start_date=start_dt.day,
            start_hour=start_dt.hour,
            start_minute=start_dt.minute,
        )
        max_airspeed_ms = airspeed_result["max_airspeed_ms"]
        print(max_airspeed_ms)
        drag_out = run_model({
            "envelope_radius": radius,
            "airspeed": max_airspeed_ms,
            "cruise_altitude": cruise_altitude_m,
        })

        drag_force_N = drag_out["drag_force_N"]
        thrust_per_prop = drag_force_N / 2
        print(drag_force_N)
        print(cruise_altitude_m)
        print()

        #calc thrust = drag/2
        #calc radius of given prop which produces that thrust at 7000 rpm
        prop_result = size_prop_radius(
            thrust_required_N=thrust_per_prop,  # drag / 2 from envelope_drag
            blade_data_file=os.path.join(os.path.dirname(__file__), "blade_data_output2.xlsx"),
            env_basepath=env.basepath,
            num_blades=3,
            hub_to_tip=0.2,
            design_airspeed=max_airspeed_ms,  #worst-case from kb_max_airspeed
            max_rpm=4000.0,
            c_tip_fraction = 1,
        )
        prop_radius = prop_result["prop_radius_m"]

        #calc peak energy consumed based on this
        sp_result = max_panels_on_envelope(
            envelope_radius=radius,
            area_per_panel=solar_area_per_panel,
        )
        max_panels = sp_result["max_panels"]
        max_solar_area = sp_result["max_solar_area_m2"]
        print(f"Max panels on envelope: {max_panels}  ({max_solar_area:.1f} m²)")

        solar_out = solar_mod.run_model({
            'start_latitude': airspeed_result["worst_leg_start_lat"],
            'start_longitude': airspeed_result["worst_leg_start_lon"],
            'destination_latitude': airspeed_result["worst_leg_end_lat"],
            'destination_longitude': airspeed_result["worst_leg_end_lon"],
            'start_year': start_dt.year,
            'start_month': start_dt.month,
            'start_day': start_dt.day,
            'start_hour': start_dt.hour,
            'start_minute': start_dt.minute,
            'duration_hours': 1200.0 / 3600.0,  #timestep_s = 1200, same as MATLAB
            'heading': airspeed_result["worst_heading_deg"],
            'cruise_altitude': cruise_altitude_m,
            'sp_area': solar_area_per_panel,
            'sp_efficiency': 0.33,  #solar_panel_eta, same as forward mode
            'req_area': max_solar_area,  #from max_panels_on_envelope
            'outer_envelope_radius': radius,
            'timestep_minutes': 10,  #solar_timestep_s/60 = 600/60, same as MATLAB
        })
        print('airspeed heading', airspeed_result["worst_heading_deg"])
        solar_energy_J = solar_out['total_energy_J']
        #energy_balance = solar_energy_J - peak_energy_J  # positive = surplus, negative = need batteries
        print(f"Solar energy generated at critical leg: {solar_energy_J:.1f} J")
        energy_per_panel_J = solar_energy_J / max_panels
        print(f"Average Solar energy generated per panel at critical leg: {energy_per_panel_J:.1f} J")
        final_solar_area = 60
        n_batteries_prelim = 4

        V_total_prelim = (4 / 3) * math.pi * radius ** 3
        A_env_prelim = 4 * math.pi * radius ** 2
        V_int_prelim = V_total_prelim - A_env_prelim * envelope_thickness
        V_bal_max_prelim = 0.0044 * V_int_prelim
        ballonet_radius_prelim = (3 * V_bal_max_prelim / (4 * math.pi)) ** (1 / 3)


        vertical_prop_radius_prelim = 0.8
        strut_radius_prelim = 0.05
        strut_radius_h_prelim = 0.05
        payload_load_patch_radius_prelim = 0.5
        payload_load_patch_loc_prelim = 0.7

        obj = Airship(
            max_airspeed_ms=max_airspeed_ms,
            energy_per_panel_J = energy_per_panel_J,
            start_year=start_dt.year,
            start_month=start_dt.month,
            start_date=start_dt.day,
            start_hour=start_dt.hour,
            start_minute=start_dt.minute,

            solar_panel_eta=0.33,

            envelope_radius=radius,
            envelope_thickness=envelope_thickness,
            envelope_mass_per_m2=envelope_mass_per_m2,

            ballonet_radius=ballonet_radius_prelim,
            ballonet_thickness=ballonet_thickness,
            ballonet_mass_per_m2=ballonet_mass_per_m2,

            solar_area_per_panel=solar_area_per_panel,
            required_solar_area=final_solar_area,
            solar_panel_weight_per_panel=solar_panel_weight_per_panel,

            battery_length=battery_length,
            battery_width=battery_width,
            battery_height=battery_height,
            energy_per_battery=energy_per_battery,
            battery_weight_per_unit_volume=battery_weight_per_unit_volume,
            number_of_batteries=n_batteries_prelim,

            vertical_prop_radius=vertical_prop_radius_prelim,
            horizontal_prop_radius=prop_radius,
            vertical_propulsor_loc=0.7,
            horizontal_propulsor_loc=0,
            horizontal_num_blades=3,
            vertical_num_blades=5,

            hub_to_tip_h=0.15,
            hub_to_tip_v=0.2,

            payload_load_patch_radius=payload_load_patch_radius_prelim,
            payload_load_patch_loc=payload_load_patch_loc_prelim,
            payload_d_factor=payload_d_factor,
            payload_weight=payload_weight,
            payload_length=payload_length,
            payload_width=payload_width,
            payload_height=payload_height,

            strut_size=2 * vertical_prop_radius_prelim,
            #strut_size_h=2 * prop_radius,
            strut_radius=strut_radius_prelim,
            strut_radius_h=strut_radius_h_prelim,

            lifting_gas_density_sl=0.0899,
            ambient_gas_density_sl=1.225,
            cruise_altitude_m=cruise_altitude_m,
        )
        display(obj)



    else:

        eng = matlab.engine.start_matlab()
        python_exe = sys.executable.replace('\\', '/')
        eng.eval(f"pyenv('Version', '{python_exe}');", nargout=0)
        optimizer_path = os.path.join(os.path.dirname(__file__), "Optimizer")
        eng.addpath(eng.genpath(optimizer_path), nargout=0)
        eng.addpath(os.path.dirname(__file__), nargout=0)
        params = {
            "optim_modules_path": env.kbe_add_path,
            "mission_plan_path" : os.path.join(os.path.dirname(__file__), "mission_plan.xlsx"),
            "blade_data_path" : os.path.join(os.path.dirname(__file__), "blade_data_output2.xlsx"),
            "start_year":start_year,
            "start_month":start_month,
            "start_date":start_date,
            "start_hour":start_hour,
            "start_minute":start_minute,
            "cruise_altitude_m":cruise_altitude_m,
            "envelope_thickness":envelope_thickness,
            "envelope_mass_per_m2":envelope_mass_per_m2,
            "gas_density":gas_density,
            "ballonet_thickness":ballonet_thickness,
            "ballonet_mass_per_m2":ballonet_mass_per_m2,
            "solar_area_per_panel":solar_area_per_panel,
            "solar_panel_weight_per_panel": solar_panel_weight_per_panel,
            "energy_per_battery": energy_per_battery,
            "battery_weight_per_unit_volume":  battery_weight_per_unit_volume,
            "battery_length":battery_length,
            "battery_width":battery_width,
            "battery_height":battery_height,
            "payload_weight":payload_weight,
            "payload_d_factor":payload_d_factor,
            "payload_length":payload_length,
            "payload_width":payload_width,
            "payload_height":payload_height,
            "load_patch_thickness":load_patch_thickness,
            "load_patch_weight_per_volume":load_patch_weight_per_volume,
        }



        eng.MainRunMe(params, nargout=0)
        obj = Airship(

            start_year=start_dt.year,
            start_month=start_dt.month,
            start_date=start_dt.day,
            start_hour=start_dt.hour,
            start_minute=start_dt.minute,

            solar_panel_eta=0.33,

            payload_weight=payload_weight,
            payload_length=payload_length,
            payload_width=payload_width,
            payload_height=payload_height,
            envelope_radius=eng.workspace["envelope_radius"],
            envelope_thickness=envelope_thickness,
            envelope_mass_per_m2 = envelope_mass_per_m2,
            solar_area_per_panel=solar_area_per_panel,
            required_solar_area=eng.workspace["solar_panel_area"],
            battery_length=battery_length,
            battery_width=battery_width,
            battery_height=battery_height,
            vertical_prop_radius=eng.workspace["prop_radius_v"],
            horizontal_prop_radius=eng.workspace["prop_radius_h"],
            vertical_propulsor_loc=0.5,
            horizontal_propulsor_loc=0,
            horizontal_num_blades=int(eng.workspace["blade_count_h"]),
            vertical_num_blades=int(eng.workspace["blade_count_v"]),
            payload_load_patch_radius=0.5,
            payload_load_patch_loc=0.7,
            solar_panel_weight_per_panel=solar_panel_weight_per_panel,
            #battery_specific_energy_density=energy_per_battery,
            battery_weight_per_unit_volume=battery_weight_per_unit_volume,
            payload_d_factor=payload_d_factor,
            strut_size=2*eng.workspace["prop_radius_v"],
            strut_size_h=2*eng.workspace["prop_radius_h"],
            strut_radius=eng.workspace["strut_radius_v"],
            strut_radius_h=eng.workspace["strut_radius_h"],
            ballonet_radius=eng.workspace["ballonet_radius"],
            ballonet_thickness=ballonet_thickness,
            ballonet_mass_per_m2=ballonet_mass_per_m2,
            #ambient_gas_mass=eng.workspace["ambient_gas_mass"],
            horizontal_prop_weight=eng.workspace["weight_propulsors_h"],
            vertical_prop_weight=eng.workspace["weight_propulsors_v"],
            #dry_gas_mass=eng.workspace["gas_mass_kg"],
            lifting_gas_density_sl=gas_density,
            ambient_gas_density_sl=1.225

        )

        eng.quit()
        display(obj)

else:
    print('User Type Not Defined')