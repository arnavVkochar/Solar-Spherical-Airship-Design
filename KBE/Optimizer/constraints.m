function [c, ceq] = constraints(x, params)
    [~, res] = run_airship_analysis(x, params);
    %constraints
    %ineq: envelope sizing
    %ineq: req solar panel area = design var solar panel area
    %envelope large enough for largest ring never below equator
    %energy balance should be positive
    %res.achievable_altitude_m should be less than res.pressure_ceiling_m
    %eq cons - achievable = cruise alt
    ceq1 = (0 - abs(res.altitude_residual_m))/params.cruise_altitude_m;
    ceq = [];
    %c = [];
    %c2 = (40 - res.horizontal_prop_eta)/40;
    %c4 = (res.rpm_h-6000)/6000;
    
    c1 = -res.Energy_balance/1e7;
    c2 = (res.altitude_residual_m - 500)/params.cruise_altitude_m;
    %c3 = (-res.altitude_residual_m - 500)/params.cruise_altitude_m;
    c3 = (params.cruise_altitude_m - res.achievable_altitude_m)/params.cruise_altitude_m;
    c4 = (100 - res.gap_to_ceiling_m)/100;
    c5 = (res.min_radius_m - res.envelope_radius)/6;
    c = [c1, c3, c4, c5];


end