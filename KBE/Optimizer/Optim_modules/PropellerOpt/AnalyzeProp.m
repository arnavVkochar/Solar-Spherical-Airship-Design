function [RPM_out, Eta_out, Power_shaft, Power_useful] = ...
         AnalyzeProp(PropDesign, TargetThrust, Airspeed, Density, KinematicViscosity, SpeedOfSound)

   Radius   = PropDesign.Radius;
   Diameter = 2 * Radius;

   function residual = thrustResidual(RPM_candidate)
      Frequency = RPM_candidate / 60;
      Omega     = 2 * pi * Frequency;
      PropDesign.performAnalysis(Airspeed, Omega, Radius, ...
                                 Density, KinematicViscosity, SpeedOfSound);
      residual = PropDesign.getThrust() - TargetThrust;
   end

   %% -------------------------------------------------------------------
   %  Sanity check
   %% -------------------------------------------------------------------
   if TargetThrust <= 0
      warning('AnalyzeProp: TargetThrust = %.4f N <= 0. Returning penalty.', TargetThrust);
      RPM_out = NaN; Eta_out = 0; Power_shaft = 1e9; Power_useful = 0;
      return;
   end

   %% -------------------------------------------------------------------
   %  Coarse scan to find a valid bracket BEFORE windmill crossover
   %
   %  Problem: at high airspeed + high RPM the prop goes windmilling and
   %  getThrust() goes negative, creating a SECOND zero crossing that
   %  fzero may find instead of the real one.
   %
   %  Strategy: scan RPM from low to high in small steps, track sign of
   %  residual, and stop as soon as we find the FIRST sign change from
   %  positive to negative (prop goes from under-thrust to over-thrust).
   %  This gives us a tight bracket in the physical operating regime.
   %% -------------------------------------------------------------------
   %scan_RPM   = 100 : 100 : 30000;     % coarse scan: 100 RPM steps
   scan_RPM   = 100 : 100 : 7000;
   scan_res   = zeros(size(scan_RPM));

   for k = 1:length(scan_RPM)
      scan_res(k) = thrustResidual(scan_RPM(k));
   end

   % Find first index where thrust crosses from BELOW target to ABOVE target
   % i.e. residual goes from negative to positive (prop ramps up with RPM)
   % OR from positive to negative on the way down after a peak.
   % We want the crossing where thrust is INCREASING through TargetThrust.
   bracket_found = false;
   for k = 1:length(scan_RPM)-1
      if scan_res(k) <= 0 && scan_res(k+1) > 0
         % Thrust crossing upward through target -- this is the real solution
         RPM_lo_bracket = scan_RPM(k);
         RPM_hi_bracket = scan_RPM(k+1);
         bracket_found  = true;
         break;
      end
   end

   % Fallback: try downward crossing (thrust peak exceeded, now decreasing)
   if ~bracket_found
      for k = 1:length(scan_RPM)-1
         if scan_res(k) >= 0 && scan_res(k+1) < 0
            % Check this isn't the windmill regime -- thrust should still be > 0
            T_at_k = scan_res(k) + TargetThrust;
            if T_at_k > 0
               RPM_lo_bracket = scan_RPM(k);
               RPM_hi_bracket = scan_RPM(k+1);
               bracket_found  = true;
               break;
            end
         end
      end
   end

   if ~bracket_found
      % Print scan diagnostics to help debug
      % fprintf('  [AnalyzeProp scan] T_target=%.2f N, V=%.2f m/s\n', TargetThrust, Airspeed);
      % fprintf('  RPM range scanned: %d to %d\n', scan_RPM(1), scan_RPM(end));
      % fprintf('  Thrust at RPM_lo : %.3f N\n', scan_res(1)   + TargetThrust);
      % fprintf('  Thrust at RPM_hi : %.3f N\n', scan_res(end) + TargetThrust);
      % fprintf('  Peak thrust found: %.3f N at RPM=%.0f\n', ...
      %         max(scan_res) + TargetThrust, scan_RPM(scan_res == max(scan_res)));
      warning('AnalyzeProp: target thrust %.2f N not achievable. Returning penalty.', TargetThrust);
      RPM_out = NaN; Eta_out = 0; Power_shaft = 1e9; Power_useful = 0;
      return;
   end

   %% -------------------------------------------------------------------
   %  Root-find within the safe bracket
   %% -------------------------------------------------------------------
   options = optimset('TolX', 0.01, 'Display', 'off');
   RPM_out = fzero(@thrustResidual, [RPM_lo_bracket, RPM_hi_bracket], options);

   %% -------------------------------------------------------------------
   %  Final analysis at solved RPM
   %% -------------------------------------------------------------------
   Frequency_out = RPM_out / 60;
   Omega_out     = 2 * pi * Frequency_out;
   J_out         = Airspeed / (Frequency_out * Diameter);

   PropDesign.performAnalysis(Airspeed, Omega_out, Radius, ...
                              Density, KinematicViscosity, SpeedOfSound);

   Eta_out      = PropDesign.Eta;
   Power_shaft  = PropDesign.getPower();
   Power_useful = TargetThrust * Airspeed;

   %% -------------------------------------------------------------------
   %  Console summary
   %% -------------------------------------------------------------------
   % fprintf('\n--- AnalyzeProp Results ---\n');
   % fprintf('  Airspeed        : %.2f m/s\n',    Airspeed);
   % fprintf('  Density         : %.4f kg/m^3\n', Density);
   % fprintf('  Kin. Viscosity  : %.3e m^2/s\n',  KinematicViscosity);
   % fprintf('  Speed of Sound  : %.2f m/s\n',    SpeedOfSound);
   % fprintf('  Target Thrust   : %.2f N\n',       TargetThrust);
   % fprintf('  Solved RPM      : %.1f rev/min\n', RPM_out);
   % fprintf('  Actual Thrust   : %.2f N\n',       PropDesign.getThrust());
   % fprintf('  Advance Ratio J : %.4f\n',         J_out);
   % fprintf('  Shaft Power     : %.2f W   <-- motor must deliver this\n', Power_shaft);
   % fprintf('  Useful Power    : %.2f W   (= T x V)\n',                   Power_useful);
   % fprintf('  Efficiency Eta  : %.2f %%\n',      Eta_out * 100);
   %if Power_shaft > 0
   %   fprintf('  Cross-check     : Puseful/Pshaft = %.2f %%  (should match Eta)\n', ...
   %           (Power_useful / Power_shaft) * 100);
   %end

end