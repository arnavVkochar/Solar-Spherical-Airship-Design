%-------------------------------------------------------------------------------
%
% GeneratePropTables.m
%
% Sweeps advance ratio J and computes Ct and Cp for a given propeller
% geometry using JavaProp. Writes two Excel files:
%   - prop_Ct_vs_J.xlsx
%   - prop_Cp_vs_J.xlsx
%
% Usage:
%   GeneratePropTables(PropDesign, Diameter, Density, KV, SpeedOfSound)
%
% Inputs:
%   PropDesign   - Propeller object already returned by DesignProp_updated()
%   Diameter     - Propeller diameter [m]
%   Density      - Air density [kg/m^3]
%   KV           - Kinematic viscosity [m^2/s]
%   SpeedOfSound - Speed of sound [m/s]
%
% The sweep is done by fixing a reference RPM and varying airspeed to
% march through J = V / (n * D).  This keeps the blade Reynolds number
% roughly constant and matches how JavaProp performAnalysis works best.
%
%-------------------------------------------------------------------------------

function GeneratePropTables(PropDesign, Diameter, Density, KV, SpeedOfSound)

    %% ------------------------------------------------------------------
    %  1.  J sweep definition
    %  Cover J = 0 (static) through a bit past zero-thrust.
    %  For an airship prop J rarely exceeds ~0.7 in practice.
    %% ------------------------------------------------------------------
    J_min  = 0.0;
    J_max  = 0.80;
    N_pts  = 50;          % number of points
    J_vec  = linspace(J_min, J_max, N_pts)';

    %% ------------------------------------------------------------------
    %  2.  Fix a reference RPM that is representative of cruise.
    %      We derive airspeed from J at each point: V = J * n * D
    %      A typical airship propeller might cruise near 2000-4000 RPM;
    %      adjust if your design point differs.
    %% ------------------------------------------------------------------
    RPM_ref   = 3000;                  % rev/min – change if needed
    n_ref     = RPM_ref / 60;          % rev/s
    Omega_ref = 2 * pi * n_ref;        % rad/s
    Radius    = Diameter / 2;

    %% ------------------------------------------------------------------
    %  3.  Allocate output vectors
    %% ------------------------------------------------------------------
    Ct_vec = zeros(N_pts, 1);
    Cp_vec = zeros(N_pts, 1);

    %% ------------------------------------------------------------------
    %  4.  Sweep
    %% ------------------------------------------------------------------
    fprintf('\n--- Ct/Cp sweep  (RPM_ref = %d) ---\n', RPM_ref);
    fprintf('%6s  %8s  %8s\n', 'J', 'Ct', 'Cp');

    for k = 1:N_pts
        J = J_vec(k);

        % Derive airspeed for this J at the reference RPM
        V = J * n_ref * Diameter;     % m/s  (= 0 when J = 0 → static)

        % JavaProp performAnalysis(V, Omega, Radius, rho, nu, a)
        PropDesign.performAnalysis(V, Omega_ref, Radius, ...
                                   Density, KV, SpeedOfSound);

        Ct_vec(k) = PropDesign.CT;    % non-dimensional thrust coefficient
        Cp_vec(k) = PropDesign.CP;    % non-dimensional power  coefficient

        fprintf('%6.3f  %8.5f  %8.5f\n', J, Ct_vec(k), Cp_vec(k));
    end

    outputComb = 'prop_Ct_Cp_vs_J.xlsx';
    if isfile(outputComb), delete(outputComb); end

    T_comb = table(J_vec, Ct_vec, Cp_vec, 'VariableNames', {'J', 'Ct', 'Cp'});
    writetable(T_comb, outputComb, 'Sheet', 'Ct_Cp_vs_J');
    fprintf('Combined table written to: %s\n\n', outputComb);

    %% ------------------------------------------------------------------
    %  8.  Print FlightGear-ready XML snippet to console
    %      (copy-paste into your <propeller> block)
    %% ------------------------------------------------------------------
    fprintf('--- FlightGear XML snippet ---\n');
    fprintf('<table name="C_THRUST" type="internal">\n');
    fprintf('  <tableData>');
    for k = 1:N_pts
        fprintf(' %.2f %.4f', J_vec(k), Ct_vec(k));
    end
    fprintf(' </tableData>\n</table>\n\n');

    fprintf('<table name="C_POWER" type="internal">\n');
    fprintf('  <tableData>');
    for k = 1:N_pts
        fprintf(' %.2f %.4f', J_vec(k), Cp_vec(k));
    end
    fprintf(' </tableData>\n</table>\n');

end