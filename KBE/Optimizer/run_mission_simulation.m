function run_mission_simulation(design_params)

optim_modules_path = design_params.optim_modules_path;
py.sys.path().insert(int32(0), optim_modules_path);

payload_weight = design_params.payload_weight;
payload_length = design_params.payload_length;
payload_width = design_params.payload_width;
payload_height = design_params.payload_height;
cruise_altitude_m = design_params.cruise_altitude_m;
envelope_thickness = design_params.envelope_thickness;
envelope_mass_per_m2 = design_params.envelope_mass_per_m2;
energy_per_panel_J = design_params.energy_per_panel_J;
solar_area_per_panel = design_params.solar_area_per_panel;
battery_length = design_params.battery_length;
battery_width = design_params.battery_width;
battery_height = design_params.battery_height;
solar_panel_weight_per_panel = design_params.solar_panel_weight_per_panel;
energy_per_battery = design_params.energy_per_battery;
battery_weight_per_unit_volume = design_params.battery_weight_per_unit_volume;
payload_d_factor = design_params.payload_d_factor;



start_year = design_params.start_year;
start_month = design_params.start_month;
start_date = design_params.start_date;
start_hour = design_params.start_hour;
start_minute = design_params.start_minute;


gas_density_sl = design_params.gas_density;
ballonet_thickness = design_params.ballonet_thickness;
ballonet_mass_per_m2 = design_params.ballonet_mass_per_m2;
%load_patch_thickness = design_params.load_patch_thickness;
%struc_material_density = design_params.load_patch_weight_per_volume;




envelope_radius = design_params.envelope_radius;
%solar_panel_area = ranges(2,1) + x(2)*(ranges(2,2)-ranges(2,1));
num_panels = design_params.num_panels;
solar_panel_area = num_panels*design_params.solar_area_per_panel;

num_battery = design_params.num_battery;
prop_radius_h =  design_params.prop_radius_h;
prop_radius_v = design_params.prop_radius_v;
strut_radius_h = 0.05;
strut_radius_v = 0.05;
%J_h = ranges(5,1) + x(5)*(ranges(5,2)-ranges(5,1));
%J_v = 0.5;
hub_to_tip_ratio_h = design_params.hub_to_tip_ratio_h;
hub_to_tip_ratio_v = design_params.hub_to_tip_ratio_v;
%blade_count_h = round(ranges(7,1) + x(7)*(ranges(7,2)-ranges(7,1)));
blade_count_h = design_params.blade_count_h;
blade_count_v = design_params.blade_count_v;
%thrust_h = ranges(8,1) + x(8)*(ranges(8,2)-ranges(8,1));
%thrust_v = 0;
%design_airspeed = ranges(9,1) + ...
%    x(9)*(ranges(9,2)-ranges(9,1));
ballonet_volume_fraction_sl = design_params.ballonet_volume_fraction_sl;

solar_panel_eta = design_params.solar_panel_eta;


rpm_arr    = design_params.rpm_arr;
thrust_arr = design_params.thrust_arr;
eta_arr    = design_params.eta_arr / 100.0; 

[thrust_arr_unique, unique_idx] = unique(thrust_arr, 'last');
rpm_arr_unique = rpm_arr(unique_idx);
eta_arr_unique = eta_arr(unique_idx);


spinner_dia_h = hub_to_tip_ratio_h*(prop_radius_h*2);
spinner_dia_v = hub_to_tip_ratio_v*(prop_radius_v*2);

fprintf('\n--------------------------------------------------------\n');
fprintf('\n--- Design Variables ---\n');
fprintf('envelope_radius  = %.4f\n', envelope_radius);
fprintf('total_solar_panel_area  = %.4fm2\n', solar_panel_area);
fprintf('num_battery = %.0f\n', ceil(num_battery));
fprintf('prop_radius_h  = %.4f\n', prop_radius_h);
fprintf('strut_radius_h  = %.4f\n', strut_radius_h);
fprintf('prop_radius_v  = %.4f\n', prop_radius_v);
fprintf('strut_radius_v  = %.4f\n', strut_radius_v);

fprintf('hub_to_tip_ratio_h  = %.4f\n', hub_to_tip_ratio_h);
fprintf('hub_to_tip_ratio_v  = %.4f\n', hub_to_tip_ratio_v);
fprintf('blade_count_h  = %.4f\n', blade_count_h);
fprintf('blade_count_v  = %.4f\n', blade_count_v);

fprintf('ballonet_volume_fraction_sl  = %.4f\n\n', ballonet_volume_fraction_sl);



if py.importlib.util.find_spec('airship_trajectory') ~= py.None
    airship_trajectory = py.importlib.import_module('airship_trajectory');
    py.importlib.reload(airship_trajectory);
else
    airship_trajectory = py.importlib.import_module('airship_trajectory');
end

timestep_s = 1200;
motor_eta = 0.9;


ceiling_tolerance_m = 500;

solar_timestep_s = timestep_s/2;

%weight_per_propulsor = 5;%kg
weight_per_battery =  battery_weight_per_unit_volume*(battery_length*battery_width*battery_height);
weight_per_load_patch = 0;
weight_prop_struts = 0;

num_load_patches = 6;

%energy_per_battery = 120000;
loiter_coef = 0.8;
penalty = 0;

weight_propulsors_h = design_params.prop_weight_h; %kg
weight_propulsors_v = design_params.prop_weight_v;


if py.importlib.util.find_spec('ground_speed') ~= py.None
    Ground_Speed_Module = py.importlib.import_module('ground_speed');
    py.importlib.reload(Ground_Speed_Module);
else
    Ground_Speed_Module = py.importlib.import_module('ground_speed');
end

py_output = Ground_Speed_Module.run_model(py.dict());


total_distance_m   = double(py_output{'total_distance_m'});
total_distance_km  = double(py_output{'total_distance_km'});
ground_speed    = double(py_output{'ground_speed_ms'});
ground_speed_kmh   = double(py_output{'ground_speed_kmh'});
num_waypoints      = double(py_output{'num_waypoints'});

%fprintf('Ground Speed =  %.4f m/s\n', ground_speed);

py_input = py.dict(pyargs( ...
    'excel_path',        design_params.mission_plan_path, ...
    'sheet_name',        'Waypoints',                    ...  
    'avg_speed_ms',      ground_speed,                           ...  
    'start_year',        start_year,                           ...  
    'start_month',       start_month,                              ...
    'start_day',         start_date,                              ...
    'start_hour',        start_hour,                              ...
    'start_minute',      start_minute,                              ...
    'timestep_minutes',  timestep_s/60                               ... 
));

py_output = airship_trajectory.run_model(py_input);


n_points = int32(py_output{'n_points'});


latitudes   = double(py_output{'latitudes'});    
longitudes  = double(py_output{'longitudes'});   
elapsed_s   = double(py_output{'elapsed_s'});    
dist_m      = double(py_output{'dist_m'});       
leg_indices = double(py_output{'leg_indices'});  



total_distance_km  = double(py_output{'total_distance_km'});
total_duration_min = double(py_output{'total_duration_min'});
n_waypoints        = int32(py_output{'n_waypoints'});
n_legs             = int32(py_output{'n_legs'});


n = double(n_points);

traj_matrix = [(0:n-1)', ...          
               latitudes(:),   ...          
               longitudes(:),  ...          
               elapsed_s(:),   ...          
               dist_m(:),      ...          
               leg_indices(:)];            

col_names = {'idx', 'lat', 'lon', 'elapsed_s', 'dist_m', 'leg'};


elapsed_min = traj_matrix(:, 4) / 60;
traj_matrix_ext = [traj_matrix, elapsed_min]; 

%disp(col_names)
%disp(traj_matrix);

%disp(traj_matrix_ext(1,1));

sz = size(traj_matrix_ext);

rows_sz = size(traj_matrix_ext, 1);
cols_sz = size(traj_matrix_ext, 2);

%disp(rows_sz)
%disp(cols_sz)

counter2 =0;%solar panels not enough
counter3 = 0;

%battery_capacity = 0;
battery_capacity = loiter_coef *num_battery*energy_per_battery;
battery_capacity_max = 0;
Energy_balance = battery_capacity; %has to be 0 or positive in the end. -> constraint put it in res
counter = 0;
%fprintf('Starting loop. \n\n\n');


RPM_res         = zeros((rows_sz-1), 1);
Eta_res         = zeros((rows_sz-1), 1);
PowerShaft_res  = zeros((rows_sz-1), 1);
PowerUseful_res = zeros((rows_sz-1), 1);


energygentotal = 0;
energycontotal = 0;
% --- Worst-leg trackers (initialised before loop) ---
worst_deficit_J  = -Inf;
worst_consumed_J = 0;
worst_solar_J    = 0;
worst_leg_idx    = -1;

for i = 1:(rows_sz-1)
    fprintf('---------------------------------------------------------------\n')
    fprintf('Iteration i = %d\n', i);

    start_lat = traj_matrix_ext(i,2);
    end_lat   = traj_matrix_ext(i+1,2);

    start_lon = traj_matrix_ext(i,3);
    end_lon   = traj_matrix_ext(i+1,3);

    timestep = traj_matrix_ext(i+1,4) - traj_matrix_ext(i,4);
   

    total_time_elapsed_s = traj_matrix_ext(i,4);
    fprintf('total time elapsed: %.3f s\n', total_time_elapsed_s);


    
    if py.importlib.util.find_spec('Time_Elapsed_Module') ~= py.None
        Time_Elapsed_Module = py.importlib.import_module('Time_Elapsed_Module');
        py.importlib.reload(Time_Elapsed_Module);
    else
        Time_Elapsed_Module = py.importlib.import_module('Time_Elapsed_Module');
    end

    py_input = py.dict(pyargs( ...
        'start_year',          start_year,   ...  
        'start_month',         start_month,      ... 
        'start_day',           start_date,     ... 
        'start_hour',          start_hour,      ...  
        'start_minute',        start_minute,     ...  
        'elapsed_seconds',     total_time_elapsed_s   ...  
    ));

    py_output = Time_Elapsed_Module.run_model(py_input);

    % Extract outputs
    new_year   = double(py_output{'new_year'});
    new_month  = double(py_output{'new_month'});
    new_day    = double(py_output{'new_day'});
    new_hour   = double(py_output{'new_hour'});
    new_minute = double(py_output{'new_minute'});
    new_datetime_str = string(py_output{'new_datetime_str'}); 
    elapsed_minutes  = double(py_output{'elapsed_minutes'});

    fprintf('Arrival time: %s\n', new_datetime_str);


    dist_m = traj_matrix_ext(i+1,5) - traj_matrix_ext(i,5);
    fprintf('Distance travelled in this section: %.3f m\n', dist_m);

    heading = azimuth(start_lat, start_lon, end_lat, end_lon);
    fprintf('Heading/Azimuth: %.3f deg\n', heading);
    
    if py.importlib.util.find_spec('wind_data') ~= py.None
        Wind_Module = py.importlib.import_module('wind_data');
        py.importlib.reload(Wind_Module);
    else
        Wind_Module = py.importlib.import_module('wind_data');
    end

    py_wind_input = py.dict(pyargs( ...
        'latitude',  start_lat, ...   
        'longitude', start_lon  ...   
    ));

    py_wind_output = Wind_Module.run_model(py_wind_input);

    
    wind_speed_mps     = double(py_wind_output{'wind_speed_mps'});      
    wind_direction_deg = double(py_wind_output{'wind_direction_deg'});
    
    fprintf('Wind speed: %.3f m/s\n', wind_speed_mps);
    fprintf('Wind direction: %.3f deg\n', wind_direction_deg);

    

    if py.importlib.util.find_spec('Wind_Vector_Module') ~= py.None
        Wind_Vector_Module = py.importlib.import_module('Wind_Vector_Module');
        py.importlib.reload(Wind_Vector_Module);
    else
        Wind_Vector_Module = py.importlib.import_module('Wind_Vector_Module');
    end

    py_input = py.dict(pyargs( ...
        'wind_speed',     wind_speed_mps,     ...  
        'wind_direction', wind_direction_deg, ...   
        'ground_speed',   ground_speed,   ...   
        'heading',        heading         ...   
    ));
    py_output = Wind_Vector_Module.run_model(py_input);
    Va_N = double(py_output{'Va_N'});
    Va_E= double(py_output{'Va_E'});
    airspeed = double(py_output{'airspeed'});  
    fprintf('Airspeed: %.3f m/s\n', airspeed);

  
    if py.importlib.util.find_spec('envelope_drag') ~= py.None
        Envelope_Drag_Module = py.importlib.import_module('envelope_drag');
        py.importlib.reload(Envelope_Drag_Module);
    else
        Envelope_Drag_Module = py.importlib.import_module('envelope_drag');
    end
    
    py_input = py.dict(pyargs( ...
        'envelope_radius', envelope_radius, ...
        'airspeed',        airspeed,        ...
        'cruise_altitude', cruise_altitude_m  ...
    ));
    
    py_output = Envelope_Drag_Module.run_model(py_input);
    
    drag_force_N           = double(py_output{'drag_force_N'});
    cd                     = double(py_output{'cd'});
    reynolds               = double(py_output{'reynolds'});
    dynamic_pressure_Pa    = double(py_output{'dynamic_pressure_Pa'});
    frontal_area_m2        = double(py_output{'frontal_area_m2'});
    air_density_kg_m3      = double(py_output{'air_density_kg_m3'});
    dynamic_viscosity_Pa_s = double(py_output{'dynamic_viscosity_Pa_s'});
    
    fprintf('Cd = %.4f\n', cd);
    fprintf('Drag force (N) = %.4f\n', drag_force_N);


    kinematic_viscosity_m2_s = dynamic_viscosity_Pa_s / air_density_kg_m3;
    
    
    gamma = 1.4;          
    R_air = 287.058;      
    temperature_K = 288.15; 
    speed_of_sound_m_s = sqrt(gamma * R_air * temperature_K);
    

    
    thrust_required_per_prop = drag_force_N / 2;
    og_trpp = thrust_required_per_prop;
    
    thrust_required_per_prop = max(thrust_required_per_prop, min(thrust_arr_unique));
    thrust_required_per_prop = min(thrust_required_per_prop, max(thrust_arr_unique));
    
    RPM_res(i) = interp1(thrust_arr_unique, rpm_arr_unique, thrust_required_per_prop, 'linear');
    RPM_res(i) = max(RPM_res(i), 0);
    
    Eta_res(i) = interp1(rpm_arr_unique, eta_arr_unique, RPM_res(i), 'linear', 'extrap');
    Eta_res(i) = max(min(Eta_res(i), 1.0), 0.01);
    
    PowerUseful_res(i) = thrust_required_per_prop * airspeed;
    PowerShaft_res(i)  = PowerUseful_res(i) / Eta_res(i);
    fprintf('Interpolated RPM: %.1f rpm\n', RPM_res(i));
    fprintf('Thrust per prop: %.3f N\n', thrust_required_per_prop);
    fprintf('Useful power: %.3f W\n', PowerUseful_res(i));
    fprintf('Interpolated eta: %.4f\n', Eta_res(i));
    fprintf('Shaft power: %.3f W\n', PowerShaft_res(i));
    fprintf('Motor eta: %.3f\n', motor_eta);
    
    if thrust_required_per_prop<og_trpp
        counter3 = 1;
    end

    if count(py.sys.path, '') == 0
        insert(py.sys.path, int32(0), '');   % make sure current folder is on path
    end
    
    try
        HTM = py.importlib.import_module('Horizontal_Thruster_Module');
        py.importlib.reload(HTM);
    catch
        HTM = py.importlib.import_module('Horizontal_Thruster_Module');
    end
    

    
    py_input = py.dict(pyargs( ...
        'power_shaft_per_thruster_W',  PowerShaft_res(i),  ...
        'motor_efficiency',            motor_eta,           ...
        'timestep_s',                  timestep_s           ...
    ));
    
    
    py_output = HTM.run_model(py_input);
    
    
    power_elec_per_thruster_W  = double(py_output{'power_elec_per_thruster_W'});
    power_elec_total_W         = double(py_output{'power_elec_total_W'});
    energy_per_thruster_J      = double(py_output{'energy_per_thruster_J'});
    total_energy_J_thruster    = double(py_output{'energy_total_J'});
    

    fprintf('Total energy used by both thrusters     : %.4f J\n',   total_energy_J_thruster);

    energycontotal = energycontotal +total_energy_J_thruster;


    %Solar panel module
    if py.importlib.util.find_spec('solar_power_generated') ~= py.None
        solar_power_generated = py.importlib.import_module('solar_power_generated');
        py.importlib.reload(solar_power_generated);
    else
        solar_power_generated = py.importlib.import_module('solar_power_generated');
    end
     
    %here there should be a model that takes start date, time and also
    %total time elapsed into account to calculate new time.
     
    py_input = py.dict(pyargs( ...
        'start_latitude',        start_lat,        ...
        'start_longitude',       start_lon,       ...
        'destination_latitude',  end_lat,  ...
        'destination_longitude', end_lon, ...
        'start_year',            new_year,            ...
        'start_month',           new_month,           ...
        'start_day',             new_day,             ...
        'start_hour',            new_hour,            ...
        'start_minute',          new_minute,          ...
        'duration_hours',        timestep_s/3600,        ...
        'heading',               heading,               ...
        'cruise_altitude',       cruise_altitude_m,       ...
        'sp_area',               solar_area_per_panel,               ...
        'sp_efficiency',         solar_panel_eta,         ...
        'req_area',              solar_panel_area,              ...
        'outer_envelope_radius', envelope_radius, ...
        'timestep_minutes',      solar_timestep_s/60       ...
    ));
     
    py_output = py.solar_power_generated.run_model(py_input);
     
     
    total_energy_wh    = double(py_output{'total_energy_wh'});
    total_energy_kwh   = double(py_output{'total_energy_kwh'});
    total_energy_J     = double(py_output{'total_energy_J'});
    peak_power_w       = double(py_output{'peak_power_w'});
    avg_power_w        = double(py_output{'avg_power_w'});
    mission_duration_h = double(py_output{'mission_duration_h'});
    %num_panels         = double(py_output{'num_panels'});
    num_rings          = double(py_output{'num_rings'});
     
     

    fprintf('  Total energy produced by solar panels: %.1f J\n',   total_energy_J);
    energygentotal = energygentotal + total_energy_J;
    
    if total_energy_J < total_energy_J_thruster
        fprintf('Used batteries for this timestep. \n\n')
        battery_capacity = battery_capacity - ...
            (total_energy_J_thruster - total_energy_J);
        if battery_capacity<0
            counter2=1;
        end
    
        if counter == 0
            battery_capacity_max = battery_capacity;
            counter = 1;
        else
            if battery_capacity_max < battery_capacity
                battery_capacity_max = battery_capacity;
            end
        end
    end
    
    if total_energy_J > total_energy_J_thruster
        if battery_capacity < (num_battery*energy_per_battery)
            battery_capacity = battery_capacity + ...
                (total_energy_J - total_energy_J_thruster);
        end
    end

    %fprintf('Battery capacity: %.3f J\n',  battery_capacity);
    %fprintf('Battery capacity max: %.3f J\n',  battery_capacity_max);

    Energy_balance = Energy_balance + total_energy_J - total_energy_J_thruster;
    fprintf('Energy balance: %.3f J\n',  Energy_balance);
    fprintf('Iteration:%.3f done \n',  i);
    fprintf('---------------------------------------------------------------\n')

    % --- Track worst leg (largest energy deficit this leg) ---
    leg_deficit_J = total_energy_J_thruster - total_energy_J;
    if leg_deficit_J > worst_deficit_J
        worst_deficit_J  = leg_deficit_J;
        worst_consumed_J = total_energy_J_thruster;
        worst_solar_J    = total_energy_J;
        worst_leg_idx    = i;
    end

end

fprintf('Final Energy balance: %.3f J\n',  Energy_balance);


strut_radius_h = 0.05;
strut_radius_v = 0.05;


weight_batteries = weight_per_battery*num_battery;
%weight_propulsors = 6*weight_per_propulsor;

total_solar_panels_weight = solar_panel_weight_per_panel *num_panels;
weight_load_patch = num_load_patches*weight_per_load_patch;



rho_air_sl = 1.225;  %kg/m³ sea level

%geo
V_int     = (4/3) * pi * (envelope_radius-envelope_thickness)^3;


V_bal_max   = ballonet_volume_fraction_sl * V_int;        

V_usable    = V_bal_max;

%ballonet_radius  = (3 * V_bal_max / (4 * pi))^(1/3);     
ambient_gas_mass = rho_air_sl * V_usable;                



dry_mass = weight_batteries+ 2*weight_propulsors_h + 4*weight_propulsors_v + weight_prop_struts + payload_weight + total_solar_panels_weight  + weight_load_patch;
fprintf('battery weight: %.3f kg\n',  weight_batteries);
fprintf('HP weight: %.3f kg\n',  2*weight_propulsors_h);
fprintf('VP weight: %.3f kg\n',  4*weight_propulsors_v);
fprintf('payload weight: %.3f kg\n',  payload_weight);
fprintf('SP weight: %.3f kg\n',  total_solar_panels_weight);
fprintf('Agm weight: %.3f kg\n',  ambient_gas_mass);
fprintf('dry mass weight: %.3f kg\n',  dry_mass);

if py.importlib.util.find_spec('envelope_buoyancy_module') ~= py.None
    Buoyancy = py.importlib.import_module('envelope_buoyancy_module');
    py.importlib.reload(Buoyancy);
else
    Buoyancy = py.importlib.import_module('envelope_buoyancy_module');
end
py_input = py.dict(pyargs( ...
        'mode',                         'constraint',              ...
        'cruise_altitude_m',             cruise_altitude_m,                 ...
        'radius',                        envelope_radius,                     ...
        'ballonet_volume_fraction_sl',   ballonet_volume_fraction_sl,                     ...
        'gas_density_sl',                gas_density_sl,        ...
        'dry_mass',                      dry_mass,              ...
        'envelope_mass_per_m2',          envelope_mass_per_m2,  ...
        'envelope_thickness',            envelope_thickness,    ...
        'ballonet_mass_per_m2',          ballonet_mass_per_m2,  ...
        'ballonet_thickness',            ballonet_thickness,    ...
        'ceiling_tolerance_m',           ceiling_tolerance_m    ...
    ));


py_output = Buoyancy.run_model(py_input);


achievable_altitude_m    = double(py_output{'achievable_altitude_m'});
altitude_residual_m = double(py_output{'altitude_residual_m'});
gap_to_ceiling_m = double(py_output{'gap_to_ceiling_m'});
gas_mass_kg = double(py_output{'gas_mass_kg'});
envelope_mass_kg= double(py_output{'envelope_mass_kg'});
ballonet_mass_kg= double(py_output{'ballonet_mass_kg'});

fprintf('achievable_altitude_m: %.3f m\n',  achievable_altitude_m);
fprintf('altitude_residual_m: %.3f m\n',  altitude_residual_m);
fprintf('gap_to_ceiling_m: %.3f m\n',  gap_to_ceiling_m);


envelope_total_struc_mass = envelope_mass_kg + ballonet_mass_kg + gas_mass_kg;


if py.importlib.util.find_spec('solar_panel_min_radius') ~= py.None
    MinRadius_Module = py.importlib.import_module('solar_panel_min_radius');
    py.importlib.reload(MinRadius_Module);
else
    MinRadius_Module = py.importlib.import_module('solar_panel_min_radius');
end

py_input = py.dict(pyargs( ...
    'req_area',               solar_panel_area,               ... 
    'area_per_panel',         solar_area_per_panel,         ... 
    'min_ring_fraction',      0.15,                   ... 
    'ring_spacing_factor',    1.0,                    ... 
    'azimuth_spacing_factor', 1.1                     ... 
));

py_output = MinRadius_Module.run_model(py_input);

min_radius_m      = 1.2*double(py_output{'min_radius_m'});
last_polar_deg    = double(py_output{'last_ring_polar_deg'});

fprintf('min radius: %.3f \n',  min_radius_m);
fprintf('Energy Gen: %.3f \n',  energygentotal);  

solar_panels_enough = true;
propeller_thrust_enough = true;

if counter2 == 1
    fprintf('\n Solar panels insufficient — estimating minimum required \n');
    solar_panels_enough=false;
    fprintf('Worst leg index          : %d\n',   worst_leg_idx);
    fprintf('Energy consumed (worst)  : %.1f J\n', worst_consumed_J);
    fprintf('Energy generated (worst) : %.1f J\n', worst_solar_J);
    fprintf('Deficit (worst)          : %.1f J\n', worst_deficit_J);

    if worst_solar_J > 0 && num_panels > 0
        %energy_per_panel_J = worst_solar_J / num_panels;
        min_panels_needed  = ceil(worst_consumed_J / energy_per_panel_J);

        fprintf('Avg energy per panel at worst leg : %.1f J\n', energy_per_panel_J);
        fprintf('Current number of panels          : %d\n',     num_panels);
        fprintf('Minimum panels needed             : %d\n',     min_panels_needed);

        if min_panels_needed <= num_panels
            % Deficit was covered by batteries — panels alone at this count
            % could theoretically suffice; battery sizing was the real issue
            fprintf(' Panel count may be adequate; check battery sizing.\n');
        else
            fprintf(' Increase panel count to %d to cover worst leg from solar alone.\n', min_panels_needed);
            fprintf('  (Assumes same avg irradiance conditions as worst leg.)\n');
        end
    else
        fprintf(' No solar energy generated at worst leg.\n');
        fprintf('  Worst-leg consumption of %.1f J must be covered by batteries.\n', worst_consumed_J);
    end
end

if counter3 ==1
    propeller_thrust_enough = false;
    disp('Propeller radius not enough - enough thrust not generated')
end
%now it has to suggest a number of panels that will be enough or say that
%its not possible for the current envelope radius so try it with max
%panels. do the same for thrust requirement.

assignin('base', 'energygentotal', energygentotal);
assignin('base', 'energycontotal', energycontotal);
assignin('base', 'solar_panels_enough', solar_panels_enough);
assignin('base', 'propeller_thrust_enough', propeller_thrust_enough);