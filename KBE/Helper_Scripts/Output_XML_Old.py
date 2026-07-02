import os
import math
import env_Arnesh as env
import pandas as pd

M_TO_FT = 3.28084
M2_TO_FT2 = M_TO_FT ** 2
M3_TO_FT3 = M_TO_FT ** 3

def write_prop_xml(xlsx_path: str, output_name: str = "prop_airshipH"):
    df = pd.read_excel(xlsx_path, usecols=["J", "Ct", "Cp"])

    # Build table rows
    def _table_rows(col: str) -> str:
        return "\n".join(
            f"  {row['J']:.9g}\t{row[col]:.9g}" for _, row in df.iterrows()
        )

    ct_rows = _table_rows("Ct")
    cp_rows = _table_rows("Cp")

    xml = f"""\
<?xml version="1.0"?>

<propeller name="prop_Airship">

  <ixx unit="KG*M2">    5.0  </ixx>
  <diameter unit="IN">  78.7 </diameter>
  <numblades>           3    </numblades>
  <gearratio>           1.0  </gearratio>

  <ct_factor>           1.0  </ct_factor>
  <cp_factor>           1.0  </cp_factor>

<table name="C_THRUST" type="internal">
  <tableData>
{ct_rows}
  </tableData>
</table>

<table name="C_POWER" type="internal">
  <tableData>
{cp_rows}
  </tableData>
</table>

</propeller>
"""

    here= os.path.dirname(os.path.abspath(__file__))
    kbe_dir= os.path.dirname(here)
    engines_dir = os.path.join(kbe_dir, "Airship", "Engines")
    os.makedirs(engines_dir, exist_ok=True)

    out_path = os.path.join(engines_dir, f"{output_name}.xml")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(xml)

    print(f"[write_prop_xml] Written → {out_path}  ({len(df)} data points)")

def _sphere_volume_m3(radius_m: float) -> float:
    return (4.0 / 3.0) * math.pi * radius_m ** 3


def write_flight_gear_xml(airship) -> None:

    r= float(airship.envelope_radius)          # m
    br= float(airship.ballonet_radius)
    r_He = (r**3 - br**3) ** (1/3)
    diameter = 2.0 * r                                 # m


    arm_h = r + float(airship.effective_strut_size_h)            # m

    arm_v_lat = r * math.sqrt(3.0) / 2.0              
    arm_v_z= -r / 2.0

    wing_area_m2 = math.pi * r ** 2

    length_ft= diameter * M_TO_FT
    volume_ft3= _sphere_volume_m3(r_He) * M3_TO_FT3
    ld_ft2= length_ft * length_ft

    ballonet_vol_ft3 = (4/3) * math.pi * br * br * br * M3_TO_FT3

    it= airship.inertia_tensor
    cog = airship.cog

    empty_mass_kg= (float(airship.structural_mass))
    payload_mass_kg = float(airship.payload.weight)


    payload_cog = airship.payload.cog



    keel_z = -(
        r +float(airship.payload_height) +float(airship.battery_height)
    )

    
    ballonet_z = -r + br


    xml = f"""\
<?xml version="1.0"?>

<?xml-stylesheet type="text/xsl" href="http://jsbsim.sourceforge.net/JSBSim.xsl"?>
<fdm_config>

 <fileheader>

  <author>Kochar</author>


  <filecreationdate></filecreationdate>
  <version></version>

  <description>JSBSim model of Airship</description>
</fileheader>
  

 <!--
 ==== Metrics ===============================================================
 -->

 <metrics>

  <wingarea unit="M2">  {wing_area_m2:.3f} </wingarea>  
  <wingspan unit="M">    {diameter:.4f} </wingspan> 
  <chord    unit="M">    {diameter:.4f} </chord>     
  <htailarea unit="M2">   0.0   </htailarea>  
  <htailarm  unit="M">    0.0   </htailarm>
  <vtailarea unit="M2">   0.0   </vtailarea>
  <vtailarm  unit="M">    0.0   </vtailarm>


<location name="AERORP"   unit="M"><x>0.0</x><y>0.0</y><z>0</z></location>
<location name="EYEPOINT" unit="M"><x>0.0</x><y>0.0</y><z>0.0</z></location>
<location name="VRP"      unit="M"><x>0.0</x><y>0.0</y><z>0.0</z></location>

 </metrics>



 <mass_balance>

  <emptywt unit="KG"> {empty_mass_kg:.4f} </emptywt>

  <ixx unit="KG*M2">  {it['Ixx']:.4f} </ixx>
  <iyy unit="KG*M2">  {it['Iyy']:.4f} </iyy>
  <izz unit="KG*M2">  {it['Izz']:.4f} </izz>
  <ixy unit="KG*M2">  {it['Ixy']:.6f} </ixy>
  <ixz unit="KG*M2">  {it['Ixz']:.6f} </ixz>
  <iyz unit="KG*M2">  {it['Iyz']:.6f} </iyz>
  <location name="CG" unit="M">
   <x> {cog.x:.1f} </x><y> {cog.y:.1f} </y><z> {cog.z:.1f} </z>
  </location>



  <pointmass name="Ballast_Center">
   <location unit="M">
    <x>  0 </x>
    <y>   0.0 </y>
    <z> 0 </z>
   </location>
   <weight unit="KG"> 20000 </weight>
  </pointmass>


 </mass_balance>

 <ground_reactions>


  <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  0.00 </x>
    <y>   0.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000  </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>

    <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  0.00 </x>
    <y>   -10.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000  </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>

    <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  0.00 </x>
    <y>   10.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000  </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>

    <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  10.00 </x>
    <y>   0.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000  </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>

      <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  -10.00 </x>
    <y>   0.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000  </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>


 </ground_reactions>

 <ground_reactions>


  <contact type="BOGEY" name="CAR_GEAR">
   <location unit="M">
    <x>  0.00 </x>
    <y>   0.00 </y>
    <z> {keel_z:.2f} </z>
   </location>
   <static_friction>  0.8 </static_friction>
   <dynamic_friction> 0.5 </dynamic_friction>
   <rolling_friction> 0.2 </rolling_friction>
   <spring_coeff unit="N/M"> 50000 </spring_coeff>
   <damping_coeff unit="N/M/SEC"> 10000 </damping_coeff>
   <max_steer unit="DEG"> 360.0 </max_steer>
   <brake_group> LEFT </brake_group>
   <retractable>0</retractable>
  </contact>


 </ground_reactions>


  <propulsion>

  <!-- [0] Horizontal PORT  — fwd/bwd + yaw differential -->
  <engine file="eng_electricH">
   <location unit="M"><x>0.0</x><y>{-arm_h:.1f}</y><z>0.0</z></location>
   <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>0.0</yaw></orient>
   <feed>0</feed>
   <thruster file="prop_airshipH">
    <location unit="M"><x>0.0</x><y>{-arm_h:.1f}</y><z>0.0</z></location>
    <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>0.0</yaw></orient>
   </thruster>
  </engine>

  <!-- [1] Horizontal STARBOARD — fwd/bwd + yaw differential -->
  <engine file="eng_electricH">
   <location unit="M"><x>0.0</x><y>{arm_h:.1f}</y><z>0.0</z></location>
   <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>0.0</yaw></orient>
   <feed>0</feed>
   <thruster file="prop_airshipH">
    <location unit="M"><x>0.0</x><y>{arm_h:.1f}</y><z>0.0</z></location>
    <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>0.0</yaw></orient>
   </thruster>
  </engine>

 <!-- [2] Vertical FORE -->
<engine file="eng_electricV">
 <location unit="M"><x> {arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense> 1 </sense>
  <location unit="M"><x> {arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [3] Vertical AFT -->
<engine file="eng_electricV">
 <location unit="M"><x>{-arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense> 1 </sense>
  <location unit="M"><x>{-arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [4] Vertical PORT -->
<engine file="eng_electricV">
 <location unit="M"><x> 0.000</x><y>{-arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense>-1 </sense>
  <location unit="M"><x> 0.000</x><y>{-arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [5] Vertical STARBOARD -->
<engine file="eng_electricV">
 <location unit="M"><x> 0.000</x><y> {arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense>-1 </sense>
  <location unit="M"><x> 0.000</x><y> {arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [6] Horizontal PORT REVERSE -->
<engine file="eng_electricH">
 <location unit="M"><x>0.0</x><y>{-arm_h:.1f}</y><z>0.0</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>180.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipH">
  <location unit="M"><x>0.0</x><y>{-arm_h:.1f}</y><z>0.0</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>180.0</yaw></orient>
 </thruster>
</engine>

<!-- [7] Horizontal STARBOARD REVERSE -->
<engine file="eng_electricH">
 <location unit="M"><x>0.0</x><y>{arm_h:.1f}</y><z>0.0</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>180.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipH">
  <location unit="M"><x>0.0</x><y>{arm_h:.1f}</y><z>0.0</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>0.0</pitch><yaw>180.0</yaw></orient>
 </thruster>
</engine>

<!-- [8] Vertical FORE REVERSE (pitch -90 → thrust downward) -->
<engine file="eng_electricV">
 <location unit="M"><x> {arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense> 1 </sense>
  <location unit="M"><x> {arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [9] Vertical AFT REVERSE -->
<engine file="eng_electricV">
 <location unit="M"><x>{-arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense> 1 </sense>
  <location unit="M"><x>{-arm_v_lat:.3f}</x><y> 0.000</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [10] Vertical PORT REVERSE -->
<engine file="eng_electricV">
 <location unit="M"><x> 0.000</x><y>{-arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense>-1 </sense>
  <location unit="M"><x> 0.000</x><y>{-arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

<!-- [11] Vertical STARBOARD REVERSE -->
<engine file="eng_electricV">
 <location unit="M"><x> 0.000</x><y> {arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
 <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 <feed>0</feed>
 <thruster file="prop_airshipV">
  <sense>-1 </sense>
  <location unit="M"><x> 0.000</x><y> {arm_v_lat:.3f}</y><z>{arm_v_z:.1f}</z></location>
  <orient  unit="DEG"><roll>0.0</roll><pitch>-90.0</pitch><yaw>0.0</yaw></orient>
 </thruster>
</engine>

 </propulsion>


 <buoyant_forces>


<property value="0.0">ballonets/in-flow-ft3ps[0]</property>

<gas_cell type="HELIUM">
 <location unit="M">
  <x> 0.0 </x>
  <y> 0.0 </y>
  <z> 0.0 </z>
 </location>
 <x_radius unit="M"> {r_He:.3f} </x_radius>
 <y_radius unit="M"> {r_He:.3f} </y_radius>
 <z_radius unit="M"> {r_He:.3f} </z_radius>
 <max_overpressure unit="PA"> 39500.0 </max_overpressure>
 <valve_coefficient unit="M4*SEC/KG"> 0.5  </valve_coefficient>
 <fullness> 1 </fullness>


 <ballonet type="AIR">
  <location unit="M">
   <x> 0.0 </x>
   <y> 0.0 </y>
   <z> {ballonet_z:.3f} </z>
  </location>
  <x_radius unit="M"> {br:.3f} </x_radius>
  <y_radius unit="M"> {br:.3f} </y_radius>
  <z_radius unit="M"> {br:.3f} </z_radius>
  <max_overpressure unit="PA"> 39500.0 </max_overpressure>
  <valve_coefficient unit="M4*SEC/KG"> 0.01 </valve_coefficient>
  <fullness> 1.0 </fullness>
 
  <blower_input>
   <function name="buoyant_forces/gas-cell/ballonet[0]/in-flow-ft3ps">
    <property>ballonets/in-flow-ft3ps[0]</property>
   </function>
  </blower_input>
 </ballonet>

</gas_cell>

</buoyant_forces>


<system name="Weigh_Off">
 <channel name="Initial_Static_Weigh_Off">

  <summer name="static-condition/net-lift-lbs">
    <input> buoyant_forces/gas-cell[0]/buoyancy-lbs </input>
    <input> -inertia/weight-lbs </input>
  </summer>

 </channel>
</system>


 <system file="instrumentation-jsbsim"/> <!-- Instruments and sensors. -->

 <flight_control name="Thrust_Vectoring_Controls">

 <property value="0.0">fcs/vertical-thrust-cmd-norm</property>
 
 <property value="0.0">fcs/engine0-cmd-norm</property>
<property value="0.0">fcs/engine1-cmd-norm</property>

<channel name="Forward">

 <!-- Forward engines: active when cmd > 0 -->
 <fcs_function name="fcs/engine0-throttle-cmd">
  <function>
   <max>
    <property>fcs/engine0-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[0]</output>
 </fcs_function>

 <fcs_function name="fcs/engine1-throttle-cmd">
  <function>
   <max>
    <property>fcs/engine1-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[1]</output>
 </fcs_function>

 <!-- Reverse engines: active when cmd < 0 -->
 <fcs_function name="fcs/engine6-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/engine0-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[6]</output>
 </fcs_function>

 <fcs_function name="fcs/engine7-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/engine1-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[7]</output>
 </fcs_function>

</channel>

<channel name="Vertical">

 <!-- Downward thrust (cmd > 0): engines 2-5 at pitch 90 -->
 <fcs_function name="fcs/engine2-throttle-cmd">
  <function>
   <max>
    <property>fcs/vertical-thrust-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[2]</output>
 </fcs_function>

 <fcs_function name="fcs/engine3-throttle-cmd">
  <function>
   <max>
    <property>fcs/vertical-thrust-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[3]</output>
 </fcs_function>

 <fcs_function name="fcs/engine4-throttle-cmd">
  <function>
   <max>
    <property>fcs/vertical-thrust-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[4]</output>
 </fcs_function>

 <fcs_function name="fcs/engine5-throttle-cmd">
  <function>
   <max>
    <property>fcs/vertical-thrust-cmd-norm</property>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[5]</output>
 </fcs_function>

 <!-- Upward thrust (cmd < 0): engines 8-11 at pitch -90 -->
 <fcs_function name="fcs/engine8-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/vertical-thrust-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[8]</output>
 </fcs_function>

 <fcs_function name="fcs/engine9-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/vertical-thrust-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[9]</output>
 </fcs_function>

 <fcs_function name="fcs/engine10-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/vertical-thrust-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[10]</output>
 </fcs_function>

 <fcs_function name="fcs/engine11-throttle-cmd">
  <function>
   <max>
    <product>
     <value>-1.0</value>
     <property>fcs/vertical-thrust-cmd-norm</property>
    </product>
    <value>0.0</value>
   </max>
  </function>
  <clipto><min>0</min><max>1</max></clipto>
  <output>fcs/throttle-pos-norm[11]</output>
 </fcs_function>

</channel>


</flight_control>

 <external_reactions>



 <!-- Translational added-mass forces — at body-frame origin -->
 <force name="added-mass-bx" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.0</y><z>0.0</z></location>
  <direction><x>1.0</x><y>0.0</y><z>0.0</z></direction>
 </force>
 <force name="added-mass-by" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.0</y><z>0.0</z></location>
  <direction><x>0.0</x><y>1.0</y><z>0.0</z></direction>
 </force>
 <force name="added-mass-bz" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.0</y><z>0.0</z></location>
  <direction><x>0.0</x><y>0.0</y><z>1.0</z></direction>
 </force>

 <!-- Pitch rotational added-mass force pair — ±1 ft in z -->
 <force name="added-mass-pitch[0]" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.0</y><z>-0.3048</z></location>
  <direction><x>1.0</x><y>0.0</y><z>0.0</z></direction>
 </force>
 <force name="added-mass-pitch[1]" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.0</y><z>0.3048</z></location>
  <direction><x>1.0</x><y>0.0</y><z>0.0</z></direction>
 </force>

 <!-- Yaw rotational added-mass force pair — ±1 ft in y -->
 <force name="added-mass-yaw[0]" frame="BODY">
  <location unit="M"><x>0.0</x><y>-0.3048</y><z>0.0</z></location>
  <direction><x>1.0</x><y>0.0</y><z>0.0</z></direction>
 </force>
 <force name="added-mass-yaw[1]" frame="BODY">
  <location unit="M"><x>0.0</x><y>0.3048</y><z>0.0</z></location>
  <direction><x>1.0</x><y>0.0</y><z>0.0</z></direction>
 </force>

</external_reactions>

 <system name="constants">

  <!-- Aerodynamic constants. -->
 <property value="{length_ft:.4f}">   aero/constants/length-ft           </property>
 <property value="{length_ft:.4f}">   aero/constants/diameter-ft         </property>
 <property value="{ld_ft2:.2f}">   aero/constants/length-diameter-ft2 </property>
 <property value="{volume_ft3:.4f}"> aero/constants/volume-ft3          </property>
 <property value="{ballonet_vol_ft3:.4f}"> aero/constants/ballonet-vol-ft3    </property>

  
 <!-- Added mass constants — sphere theory -->
 <property value="0.50"> aero/constants/added-mass/k-axial      </property>  <!-- k_a sphere = 0.5 -->
 <property value="0.50"> aero/constants/added-mass/k-traverse   </property>  <!-- k_b sphere = 0.5 -->
 <property value="0.69"> aero/constants/added-mass/k-rotational </property>



</system>

 <aerodynamics file="Systems/datcom_aero"/>

</fdm_config>
"""

    here       = os.path.dirname(os.path.abspath(__file__))
    kbe_dir    = os.path.dirname(here)
    output_dir = os.path.join(kbe_dir, "Airship")
    os.makedirs(output_dir, exist_ok=True)

    out_path = os.path.join(output_dir, "Airship.xml")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(xml)

    print(f"[write_flight_gear_xml] Written → {out_path}")
    print(f"  envelope_radius : {r:.3f} m")
    print(f"  empty_mass      : {empty_mass_kg:.2f} kg  (envelope + solar)")
    print(f"  payload_mass    : {payload_mass_kg:.2f} kg")
    print(f"  Ixx/Iyy/Izz     : {it['Ixx']:.1f} / {it['Iyy']:.1f} / {it['Izz']:.1f} kg·m²")
    print(f"  CG              : ({cog.x:.3f}, {cog.y:.3f}, {cog.z:.3f}) m")
    print(f"  arm_h           : {arm_h:.3f} m  (horizontal propulsors)")
    print(f"  arm_v_lat       : {arm_v_lat:.3f} m  (vertical propulsor x/y, sphere surface at 30°)")
    print(f"  arm_v_z         : {arm_v_z:.3f} m  (vertical propulsor z)")
    print(f"  keel_z          : {keel_z:.3f} m")