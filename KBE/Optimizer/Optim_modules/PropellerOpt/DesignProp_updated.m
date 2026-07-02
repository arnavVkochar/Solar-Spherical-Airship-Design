%-------------------------------------------------------------------------------
%
% DesignProp.m
% Propeller design function using the JavaProp library.
%
% Returns a configured and designed Propeller object (PropDesign) that can
% be passed to AnalyseProp.m for performance evaluation.
%
% Usage:
%   PropDesign = DesignProp();
%
% Requires:
%   JavaProp.jar and MHClasses.jar in the working directory (or set basepath).
%
% Martin Hepperle / adapted workflow
% JavaProp is Copyright 2001-2011 Martin Hepperle
% http://www.mh-aerotools.de/airfoils/javaprop.htm
%
%-------------------------------------------------------------------------------

function PropDesign = DesignProp_updated(Diameter, Airspeed, RPM, Thrust, SpinDiameter, BladeCount, Density, KV,sound_speed )

   %% -----------------------------------------------------------------------
   %  1. Java classpath setup
   %  Add the JavaProp and MHClasses JARs to the Java classpath.
   %  Adjust 'basepath' to match your installation directory.
   %% -----------------------------------------------------------------------
   
   env = py.importlib.import_module('env_Arnesh');
   basepath = char(env.basepath);
   addpath(char(env.kbe_root));
   %basepath = "C:\Users\Arnav\Desktop\Career\MSc Aerospace\KBE\parapy_tutorial\ProjectUpdated\KBE\Optimizer\Optim_modules\PropellerOpt";
   %addpath('C:\Users\Arnav\Desktop\Career\MSc Aerospace\KBE\parapy_tutorial\ProjectUpdated\KBE');
   javaaddpath(fullfile(basepath, 'JavaProp.jar'));
   javaaddpath(fullfile(basepath, 'MHClasses.jar'));

   %% -----------------------------------------------------------------------
   %  2. Discretisation
   %  25–50 blade elements gives sufficient accuracy; more increases run time.
   %% -----------------------------------------------------------------------
   blade_sections = 40;

   %% -----------------------------------------------------------------------
   %  3. Create the Propeller object
   %% -----------------------------------------------------------------------
   PropDesign      = javaObject('MH.JavaProp.Propeller', blade_sections);
   PropDesign.Name = 'JavaProp-Design';

   %% -----------------------------------------------------------------------
   %  4. Atmosphere
   %% -----------------------------------------------------------------------
   PropDesign.Density            = Density;        % kg/m^3   (ISA sea level)
   PropDesign.KinematicViscosity = KV;     % m^2/s
   PropDesign.SpeedOfSound       = sound_speed;         % m/s

   %% -----------------------------------------------------------------------
   %  5. Airfoil distribution
   %
   %  Section index reference:
   %    1  Flat plate,  Re = 100 000
   %    2  Flat plate,  Re = 500 000
   %    3  Clark Y,     Re =  25 000
   %    4  Clark Y,     Re = 100 000
   %    5  Clark Y,     Re = 500 000
   %    6  E 193,       Re = 100 000
   %    7  E 193,       Re = 300 000
   %    8  ARA D 6%,    Re =  50 000
   %    9  ARA D 6%,    Re = 100 000
   %   10  MH 126,      Re = 500 000
   %   11  MH 112 16.2%,Re = 500 000
   %   12  MH 114 13%,  Re = 500 000
   %   13  MH 116 9.8%, Re = 500 000
   %   14  MH 120 11.7%,Re = 400 000, M = 0.75
   %   15  Read from af_1.afl / af_1.xml in JP directory
   %   16  Read from af_2.afl / af_2.xml in JP directory
   %% -----------------------------------------------------------------------
   PropDesign.removeAirfoils();   % Clear built-in defaults first

   % Root section – Clark Y at low Re (inboard flow is slower)
   PropDesign.addAirfoil(0.000,  createAirfoil(13));  % MH 116 9.8%, Re=500k
   PropDesign.addAirfoil(0.333,  createAirfoil(13));
   PropDesign.addAirfoil(2/3,    createAirfoil(12));  % MH 114 13%, Re=500k
   PropDesign.addAirfoil(1.000,  createAirfoil(10));  % MH 126, Re=500k

   %% -----------------------------------------------------------------------
   %  6. Design angle-of-attack distribution (degrees)
   %% -----------------------------------------------------------------------
   PropDesign.addAlfa(0.00, 3.0);
   PropDesign.addAlfa(0.25, 3.0);
   PropDesign.addAlfa(0.50, 3.0);
   PropDesign.addAlfa(0.75, 3.0);
   PropDesign.addAlfa(1.00, 3.0);

   %% -----------------------------------------------------------------------
   %  7. Geometry
   %% -----------------------------------------------------------------------
   %Diameter   = dia;                          % m
   Radius     = Diameter / 2;

   %SpinDiameter           = 0.126;             % m  (spinner / hub)
   PropDesign.BladeCount  = BladeCount;
   PropDesign.rRSpinner   = SpinDiameter / Diameter;

   PropDesign.removeShroud();                  % Free-tip (no shroud / duct)
   PropDesign.hasSquareTips = 0;               % Rounded tips

   %% -----------------------------------------------------------------------
   %  8. Design operating point
   %
   %  Specify either Thrust [N] OR Power [W] – set the other to zero.
   %  If both are zero, Torque [Nm] is used to derive Power.
   %% -----------------------------------------------------------------------
   %Airspeed = 30.0;                            % m/s  (forward flight speed)
   %RPM      = 5000;                            % rev/min

   Frequency = RPM / 60;                       % Hz
   Omega     = 2 * pi * Frequency;             % rad/s

   Power  = 0;                                 % W   (set to 0 → use Thrust)
   %Thrust = 10;                                % N
   Torque = 0.915;                             % Nm  (fallback if Power=Thrust=0)

   % Priority: Thrust > Torque > Power
   if Power == 0 && Thrust == 0
      Power = Torque * Omega;
   end

   %% -----------------------------------------------------------------------
   %  9. Optional blade-geometry modifiers (identity values → no effect)
   %% -----------------------------------------------------------------------
   PropDesign.incrementBladeAngle(0);   % Constant offset to local Beta [deg]
   PropDesign.multiplyBladeAngle(1);    % Scale factor on local Beta
   PropDesign.incrementChord(0);        % Constant offset to local c/R
   PropDesign.multiplyChord(1);         % Scale factor on local c/R
   PropDesign.taperChord(1);            % Linearly varying c/R scale factor

   %% -----------------------------------------------------------------------
   %  10. Run the Betz optimum design
   %% -----------------------------------------------------------------------
   %fprintf('  Thrust  designed for: %.2f N\n',   Thrust);
   PropDesign.performPropellerDesign(Airspeed, Omega, Radius, Power, Thrust);

   %% -----------------------------------------------------------------------
   %  11. Quick design-point analysis (sets Eta, CT, CP etc.)
   %% -----------------------------------------------------------------------
   J = Airspeed / (Frequency * Diameter);
   PropDesign.performAnalysis(Airspeed, Omega, Radius, Density, KV, sound_speed);

   %% -----------------------------------------------------------------------
   %  12. Console summary
   %% -----------------------------------------------------------------------
   %fprintf('\n--- PropDesign Summary ---\n');
   %fprintf('  Name      : %s\n',  char(PropDesign.Name));
   %fprintf('  Blades    : %d\n',  PropDesign.BladeCount);
   %fprintf('  Diameter  : %.3f m  (%.1f in)\n', Diameter, Diameter * 39.3701);
   %fprintf('  Spinner   : %.3f m  (%.1f in)\n', SpinDiameter, SpinDiameter * 39.3701);
   %fprintf('  RPM       : %d\n',  RPM);
   %fprintf('  Airspeed  : %.1f m/s\n', Airspeed);
   %fprintf('  J (V/nD)  : %.4f\n', J);
   %fprintf('  Thrust    : %.2f N\n',   PropDesign.Thrust);
   %fprintf('  Power     : %.2f W\n',   PropDesign.Power);
   %fprintf('  Torque    : %.3f Nm\n',  Torque);
   %fprintf('  Pitch     : %.1f deg  (%.3f m / %.1f in)\n', ...
   %        PropDesign.getBladeAngle, PropDesign.getBladePitch, ...
   %        PropDesign.getBladePitch * 39.3701);
   %fprintf('  Ct        : %.4f\n', PropDesign.CT);
   %fprintf('  Cp        : %.4f\n', PropDesign.CP);
   %fprintf('  Efficiency: %.2f %%\n', PropDesign.Eta * 100);

   %% -----------------------------------------------------------------------
   %  13. Export blade chord / twist distribution to Excel
   %% -----------------------------------------------------------------------
   exportBladeDistribution(PropDesign, blade_sections);

   %% -----------------------------------------------------------------------
   %  14. Make PropDesign available in the base workspace as well
   %% -----------------------------------------------------------------------
   assignin('base', 'PropDesign', PropDesign);

end % DesignProp

%===============================================================================
%  Helper: createAirfoil
%===============================================================================
function theAirfoil = createAirfoil(AirfoilNo)
   % Instantiate and initialise an Airfoil object from the JavaProp library.
   % AirfoilNo – integer index (see section list in DesignProp above).
   %
   % To use a polar read from file, call:
   %   theAirfoil.setBaseDir('path/to/directory');
   %   theAirfoil.Init(15);   % or 16

   theAirfoil = javaObject('MH.AeroTools.Airfoils.Airfoil');
   theAirfoil.Init(AirfoilNo);
end


function exportBladeDistribution(PropDesign, blade_sections)
   % Parse the JavaProp text output and write r/R, c/c_max, Beta to Excel.

   rawText = char(PropDesign.toText(true, true, 'r/R', 'c/R', 'Beta'));
   tokens  = strsplit(rawText, 'Beta');

   rR    = zeros(blade_sections, 1);
   cR    = zeros(blade_sections, 1);
   twist = zeros(blade_sections, 1);

   for i = 1:blade_sections
      base = 20 + (i - 1) * 19;

      rR_raw  = regexp(tokens{base + 1}, '[\d.E+-]+$', 'match');
      rR(i)   = str2double(rR_raw{end});
      cR(i)   = str2double(tokens{base + 2});
      twist(i)= str2double(tokens{base + 3});
   end

   % Normalise chord to maximum chord (c/c_max)
   c_max   = max(cR);
   c_c_max = cR / c_max;

   % Remove hub/spinner stations where chord is zero (inside spinner radius)
    validIdx = cR > 0;
    rR_valid   = rR(validIdx);
    c_c_max    = c_c_max(validIdx);
    twist      = twist(validIdx);
    
    % Re-normalise r/R so the remaining stations run cleanly from 0 to 1
    % (spinner offset will be applied externally in ParaPy)
    n_valid = sum(validIdx);
    rR      = linspace(0, 1, n_valid)';

   T = table(rR, c_c_max, twist, ...
             'VariableNames', {'r_R', 'c_cmax', 'twist_deg'});

   outputFile = 'blade_data_output2.xlsx';

    % Force delete with verification
    if isfile(outputFile)
        delete(outputFile);
        
    end

    % Write without specifying Sheet name to avoid append behavior
    writetable(T, outputFile, 'Sheet', 1, 'WriteVariableNames', true);
end