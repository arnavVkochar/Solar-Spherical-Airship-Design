###############################################################################
##
## Spherical Solar Airship
##
##  Adapted from Zeppelin NT-07 by Anders Gidenstam (GPL v2+)
##
###############################################################################

var weight_on_gear_p = "/fdm/jsbsim/forces/fbz-gear-lbs";
var ballast_p = "/fdm/jsbsim/inertia/pointmass-weight-lbs[0]";

var fake_electrical = func(reinit=0) {
    print("[Airship] Electrical ... OK (simulated)");
}


var init_all = func(reinit=0) {
    fake_electrical(reinit);
    gui.menuEnable("autopilot", 0);
    initial_weighoff();
    if (!reinit) {
        settimer(func {
            foreach (var c;
                     props.globals.getNode("/ai/models").
                         getChildren("carrier")) {
                mooring.add_ai_mooring(c, 160.0);
            }
        }, 0.0);
    }
    print("[Airship] Systems ... Check");
}

var _initialized = 0;
setlistener("/sim/signals/fdm-initialized", func {
    init_all(_initialized);
    _initialized = 1;
});

settimer(func {
    print("[Airship] Ballast confirmed: ", getprop(ballast_p), " lbs");
}, 3.5);



var initial_weighoff = func {
    settimer(auto_weighoff, 0.5);
    settimer(auto_weighoff, 1.5);
    settimer(auto_weighoff, 3.0);  # final pass after full settle
};


###############################################################################
# Flight controls — initialise and helpers

setlistener("/sim/signals/fdm-initialized", func {
    setprop("/fdm/jsbsim/fcs/engine0-cmd-norm", 0.0);
    setprop("/fdm/jsbsim/fcs/engine1-cmd-norm", 0.0);
    setprop("/fdm/jsbsim/fcs/vertical-thrust-cmd-norm",      0.0);
    setprop("/fdm/jsbsim/fcs/ballonet-inflation-cmd-norm[0]",0.0);
    print("[Airship] FDM initialised — controls zeroed.");
});

var _clamp = func(v, lo, hi) { v < lo ? lo : (v > hi ? hi : v); };

# Forward / backward — uses its own property; FlightGear never touches this.
var adj_forward = func(delta) {
    var v = _clamp(
        (getprop("/fdm/jsbsim/fcs/forward-thrust-cmd-norm") or 0) + delta,
        -1.0, 1.0);
    setprop("/fdm/jsbsim/fcs/forward-thrust-cmd-norm", v);
};

var adj_yaw = func(delta) {
    var v = _clamp(
        (getprop("/fdm/jsbsim/fcs/rudder-cmd-norm") or 0) + delta,
        -1.0, 1.0);
    setprop("/fdm/jsbsim/fcs/rudder-cmd-norm", v);
};

var stop_all = func {
    setprop("/fdm/jsbsim/fcs/engine0-cmd-norm", 0.0);
    setprop("/fdm/jsbsim/fcs/engine1-cmd-norm", 0.0);
    setprop("/fdm/jsbsim/fcs/vertical-thrust-cmd-norm",      0.0);
    print("[Airship] All thrust stopped.");
};

###############################################################################
# Unit conversion — metric display properties

var _metric_update = func {
    setprop("/airship/display/altitude-m",
            (getprop("/position/altitude-ft") or 0) * 0.3048);

    var vn = ((getprop("/fdm/jsbsim/velocities/vn-fps") or 0) -
              (getprop("/environment/wind-from-north-fps") or 0)) * 0.3048;
    var ve = ((getprop("/fdm/jsbsim/velocities/ve-fps") or 0) -
              (getprop("/environment/wind-from-east-fps") or 0)) * 0.3048;
    setprop("/airship/display/airspeed-mps", math.sqrt(vn*vn + ve*ve));

    var net_lift_lbs = getprop("/fdm/jsbsim/static-condition/net-lift-lbs") or 0;
    setprop("/airship/display/net-lift-kg", net_lift_lbs * 0.453592);

    var ballonet_vol_ft3 = getprop("/fdm/jsbsim/buoyant_forces/gas-cell/ballonet[0]/volume-ft3") or 0;
    setprop("/airship/display/ballonet-volume-m3", ballonet_vol_ft3 * 0.0283168);

    var envelope_psf = getprop("/fdm/jsbsim/buoyant_forces/gas-cell/pressure-psf") or 0;
    setprop("/airship/display/envelope-pressure-pa", envelope_psf * 47.8803);

    var envelope_vol_ft3 = getprop("/fdm/jsbsim/buoyant_forces/gas-cell/volume-ft3") or 0;
    setprop("/airship/display/envelope-volume-m3", envelope_vol_ft3 * 0.0283168);
};

var _metric_timer = maketimer(0.5, _metric_update);

setlistener("/sim/signals/fdm-initialized", func {
    setprop("/airship/display/altitude-m",           0.0);
    setprop("/airship/display/airspeed-mps",         0.0);
    setprop("/airship/display/envelope-pressure-pa", 0.0);
    setprop("/airship/display/envelope-volume-m3", 0.0);
    _metric_timer.start();
});

###############################################################################
# Altitude hold

var _alt_hold_active   = 0;
var _alt_hold_target   = 0;
var _alt_hold_timer    = nil;
var _alt_hold_integral = 0.0;

var ALT_GAIN_P  =  0.002;
var ALT_GAIN_I  =  0.0002;
var ALT_I_LIMIT =  0.80;
var ALT_CMD_MAX =  1.00;
var ALT_DT      =  0.5;

var alt_hold_start = func {
    _alt_hold_target   = getprop("/position/altitude-ft") or 0;
    _alt_hold_integral = 0.0;
    _alt_hold_active   = 1;
    if (_alt_hold_timer != nil) _alt_hold_timer.stop();
    _alt_hold_timer = maketimer(ALT_DT, _alt_hold_loop);
    _alt_hold_timer.start();
    print("[Airship] Altitude hold ON at ", _alt_hold_target, " ft");
};

var alt_hold_stop = func {
    _alt_hold_active   = 0;
    _alt_hold_integral = 0.0;
    if (_alt_hold_timer != nil) _alt_hold_timer.stop();
    setprop("/fdm/jsbsim/fcs/vertical-thrust-cmd-norm", 0.0);
    print("[Airship] Altitude hold OFF");
};

var _alt_hold_loop = func {
    if (!_alt_hold_active) return;

    var err = _alt_hold_target - (getprop("/position/altitude-ft") or 0);

    _alt_hold_integral = _clamp(
        _alt_hold_integral + err * ALT_DT,
        -ALT_I_LIMIT / ALT_GAIN_I,
         ALT_I_LIMIT / ALT_GAIN_I
    );

    var cmd = ALT_GAIN_P * err + ALT_GAIN_I * _alt_hold_integral;
    setprop("/fdm/jsbsim/fcs/vertical-thrust-cmd-norm",
            _clamp(cmd, -ALT_CMD_MAX, ALT_CMD_MAX));
};

###############################################################################
# Ballonet volume regulator
#
# The envelope volume is geometrically fixed. As altitude increases, ambient
# pressure drops and the helium expands. The ballonet must shrink accordingly
# to yield space. The target ballonet volume is derived from the ideal gas law:
#
#   V_bal_target(h) = V_total - V_He0 / p_ratio(h)
#
# where V_He0 = V_total - V_bal_ref (ground-state helium volume),
# and p_ratio(h) = exp(-0.0000368 * h_ft)  [ISA approximation].
#
# Control law:
#   err > 0  (ballonet too large) -> vent   (negative cmd -> valve opens)
#   err < 0  (ballonet too small) -> inflate (positive cmd -> blower runs)
#
# V_bal_ref is captured 2 s after FDM init to let JSBSim settle.

var BLNT_V_TOTAL = 118.32;
var BLNT_GAIN_P  =  0.05;      # cmd per ft3 of volume error; tune if oscillatory
var BLNT_CMD_MAX =  1.0;
var BLNT_DT      =  0.5;       # loop interval (s)


var _blnt_reg_timer = nil;

var _blnt_vol_ref = 0.0;   # captured at init = sea-level full ballonet volume

var _blnt_reg_loop = func {
    var alt_ft     = getprop("/position/altitude-ft") or 0;
    var vol_ft3    = getprop("/fdm/jsbsim/buoyant_forces/gas-cell/ballonet[0]/volume-ft3") or 0;

    # At altitude, ballonet should shrink proportionally with pressure
    # p_ratio < 1 at altitude, so target < ref (ballonet shrinks)
    var p_ratio    = math.exp(-0.0000368 * alt_ft);
    var vol_target = _blnt_vol_ref * p_ratio;

    var err   = vol_ft3 - vol_target;   # positive = too much air = vent
    var flow  = err < 0 ? _clamp(-BLNT_GAIN_P * err * 10.0, 0.0, 10.0) : 0.0;
    var valve = err > 0 ? _clamp( BLNT_GAIN_P * err,        0.0,  1.0) : 0.0;

    print("[Ballonet] alt=", alt_ft, " vol=", vol_ft3, " target=", vol_target,
          " err=", err, " flow=", flow, " valve=", valve);

    setprop("/fdm/jsbsim/ballonets/in-flow-ft3ps[0]", flow);
    setprop("/fdm/jsbsim/buoyant_forces/gas-cell/ballonet[0]/valve_open", valve);
};

setlistener("/sim/signals/fdm-initialized", func {
    settimer(func {
        var v = getprop("/fdm/jsbsim/buoyant_forces/gas-cell/ballonet[0]/volume-ft3");
        if (v != nil and v > 0) _blnt_vol_ref = v;
        print("[Airship] Ballonet reference volume: ", _blnt_vol_ref, " ft3");

        if (_blnt_reg_timer != nil) _blnt_reg_timer.stop();
        _blnt_reg_timer = maketimer(BLNT_DT, _blnt_reg_loop);
        _blnt_reg_timer.start();
        print("[Airship] Ballonet volume regulator ... ON");
    }, 2.0);
});

###############################################################################
# Gas valve control

var step_gas_valve_cmd = func(d) {
    var p = "/fdm/jsbsim/buoyant_forces/gas-cell[0]/valve_open";
    var t = getprop(p) + d;
    if (t > 1.0) { t = 1.0; }
    if (t < 0.0) { t = 0.0; }
    setprop(p, t);
    gui.popupTip("Gas valve " ~
                 (t ? (int(100*t + 0.005) ~ "% open.") : "closed."));
}

###############################################################################
var drop_ballast = func {
    interpolate(ballast_p, 0.0, 0.5);
    gui.popupTip("Ballast dropped!");
};


# Debug display

var debug_display_view_handler = {
    init : func {
        if (contains(me, "left")) return;

        me.left  = screen.display.new(20, 10);
        me.left.format  = "%.5g";
        me.right = screen.display.new(-250, 20);
        me.right.format = "%.4g";

        # Static condition
        me.left.add("/airship/display/ballonet-volume-m3");
        me.left.add("/airship/display/net-lift-kg");

        # Thrust and control commands
        me.right.add("/fdm/jsbsim/fcs/engine0-cmd-norm");
        me.right.add("/fdm/jsbsim/fcs/engine1-cmd-norm");
        me.right.add("/fdm/jsbsim/fcs/vertical-thrust-cmd-norm");
        me.right.add("/fdm/jsbsim/fcs/ballonet-inflation-cmd-norm[0]");
        #me.right.add("/airship/display/altitude-m");
        me.right.add("/airship/display/airspeed-mps");

        me.shown = 1;
        me.stop();
    },
    start : func {
        if (!me.shown) {
            me.left.toggle();
            me.right.toggle();
        }
        me.shown = 1;
    },
    stop : func {
        if (me.shown) {
            me.left.toggle();
            me.right.toggle();
        }
        me.shown = 0;
    }
};

setlistener("/sim/signals/fdm-initialized", func {
    var views = [
        "Helicopter View",
        "Pilot View",
        "Copilot View",
        "Chase View",
        "Tower View",
        "Chase View (Padlock)",
        "Model View",
        "Fly-By View",
    ];
    foreach (var v; views) {
        view.manager.register(v, debug_display_view_handler);
    }
    print("[Airship] Debug instrumentation ... check");
});

###############################################################################
# About dialog

var ABOUT_DLG = 0;

var dialog = {
    init : func(x = nil, y = nil) {
        me.x = x;
        me.y = y;
        me.bg = [0, 0, 0, 0.3];
        me.fg = [[1.0, 1.0, 1.0, 1.0]];
        me.title = "About";
        me.dialog = nil;
        me.namenode = props.Node.new({"dialog-name" : me.title});
    },
    create : func {
        if (me.dialog != nil) me.close();

        me.dialog = gui.Widget.new();
        me.dialog.set("name", me.title);
        if (me.x != nil) me.dialog.set("x", me.x);
        if (me.y != nil) me.dialog.set("y", me.y);

        me.dialog.set("layout", "vbox");
        me.dialog.set("default-padding", 0);

        var titlebar = me.dialog.addChild("group");
        titlebar.set("layout", "hbox");
        titlebar.addChild("empty").set("stretch", 1);
        titlebar.addChild("text").set("label", "About");
        var w = titlebar.addChild("button");
        w.set("pref-width", 16);
        w.set("pref-height", 16);
        w.set("legend", "");
        w.set("default", 0);
        w.set("key", "esc");
        w.setBinding("nasal", "ZLTNT.dialog.destroy();");
        w.setBinding("dialog-close");
        me.dialog.addChild("hrule");

        var content = me.dialog.addChild("group");
        content.set("layout", "vbox");
        content.set("halign", "center");
        content.set("default-padding", 5);
        props.globals.initNode("sim/about/text",
             "Spherical Solar Airship for FlightGear\n" ~
             "Copyright (C) 2026  Aerolympics\n\n" ~
             "Based on ZLT NT-07 model by Anders Gidenstam\n" ~
             "FlightGear flight simulator\n" ~
             "Copyright (C) 1996 - 2026  http://www.flightgear.org\n\n" ~
             "This is free software, and you are welcome to\n" ~
             "redistribute it under certain conditions.\n" ~
             "See the GNU GENERAL PUBLIC LICENSE Version 2 for the details.",
             "STRING");
        var text = content.addChild("textbox");
        text.set("halign", "fill");
        text.set("pref-width", 400);
        text.set("pref-height", 300);
        text.set("editable", 0);
        text.set("property", "sim/about/text");

        fgcommand("dialog-new", me.dialog.prop());
        fgcommand("dialog-show", me.namenode);
    },
    close : func {
        fgcommand("dialog-close", me.namenode);
    },
    destroy : func {
        ABOUT_DLG = 0;
        me.close();
        delete(gui.dialog, "\"" ~ me.title ~ "\"");
    },
    show : func {
        if (!ABOUT_DLG) {
            ABOUT_DLG = 1;
            me.init(400, getprop("/sim/startup/ysize") - 500);
            me.create();
        }
    }
};

var about = func {
    dialog.show();
}
