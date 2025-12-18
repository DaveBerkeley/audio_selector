
include <nuts.scad>
include <iec_mains.scad>

$fn = 100;

adc_dx = 50;
adc_dy = 40;
adc_thick = 1.5;
adc_pitch = 20;

// jack socket on ADC
jack_r = 7.5/2;
jack_dz = 6.2;
jack_dx = 16.5;
jack_x0 = -4;
jack_y0 = 15;

// toslink port
opto_dx = 9.7;
opto_dy = 8.9;
opto_z0 = 4;
opto_pitch = 10.8;

// pmod breakout
tang_nano_dx = 68.4;
tang_nano_dy = 43.7;
pmod_dx = 16;
pmod_dy = 8.3;
pmod_dz = 5.5;
pmod_pitch = 22.86;
pmod_x0 = 1;
pmod_y0 = -7;
pmod_z0 = 2;

// PSU board
psu_dx = 65.6;
psu_dy = 43.5;
psu_dz = 4;
psu_z0 = 6;
// PSU mounting holes
psu_hole_r = m3_hole_r;
psu_thread_r = m3_thread_r;
psu_hole_x0 = 4;
psu_hole_y0 = 4;
psu_hole_dx = 56.5;
psu_hole_dy = 35;
psu_hole_d = 4;

psu_points = [
    [ psu_hole_x0, psu_hole_y0 ],
    [ psu_hole_x0 + psu_hole_dx, psu_hole_y0 ],
    [ psu_hole_x0 + psu_hole_dx, psu_hole_y0 + psu_hole_dy ],
    [ psu_hole_x0, psu_hole_y0 + psu_hole_dy ],
];

psu_x0 = 30;
psu_y0 = -15 - psu_dy;

// base
base_dx = 130;
base_dy = 170;
base_thick = 2;
// back panel
bp_dx = 100;
bp_dy = base_dy;
bp_dz = 45;
bp_thick = 2;

y0 = -70;
panel_offset = [ -bp_thick, y0, -bp_thick ];

// mains switch cutout
sw_dy = 13;
sw_dx = 19.2;
sw_x0 = 13;
sw_y0 = 15;

// bracket
br_h = 18;
br_w = 8;
br_d = 10;
br_t = 4;
br_hole_r = m3_hole_r;
br_thread_r = m3_thread_r;
br_ys = [ 0, ((bp_dy-br_w)/2) - 21, bp_dy-br_w, ];

// Third party strip of 8 WS2812 LEDs

led_dx = 54.4;
led_dy = 10.25;
led_pcb = 1.3;
led_component = 2.3;
led_thick = 3;
led_led_dx = 5;
led_led_dy = 5;
led_led_pitch = 6.6;
led_led_y0 = 1;
led_hole_r = m3_thread_r;
led_hole_pitch = 27.1;
led_hole_y0 = 7.5;

// rotational encoder

rot_r = 0.2 + (6.9 / 2);
rot_x0 = bp_dz / 2;
rot_y0 = bp_dy - 20;

// U shaped top section

top_thick = base_thick;
top_rim_thick = 2;
top_rim_w = 2;
top_dz = bp_dz + top_thick;
top_dx = base_dx + top_thick + top_rim_thick;
top_dy = base_dy;

top_fix_hole_r = m3_hole_r;
top_fix_thread_r = m3_thread_r;
top_fix_xs = [ base_dx/3, 3*base_dx/4 ];
top_fix_z0 = 10;

    /*
    *
    */

module psu()
{
    translate( [ 0, 0, psu_z0 ] )
    difference()
    {
        cube([ psu_dx, psu_dy, psu_dz ] );

        for (xy = psu_points)
        {
            translate([ xy[0], xy[1], -0.01 ])
            cylinder(h=psu_dz+0.02, r=psu_hole_r);
        }
    }
}

    /*
    *
    */

module tang_nano()
{
    cube( [ tang_nano_dx, tang_nano_dy, 4 ] );
    for (i = [ 0 : 2 ])
    {
        x = pmod_x0 + (i * pmod_pitch);

        for (y = [ pmod_y0, tang_nano_dy - (pmod_dy + pmod_y0) ])
        {
            translate([ x, y, pmod_z0 ])
            cube([ pmod_dx, pmod_dy, pmod_dz, ] );
        }
    }
}

    /*
    *
    */

module opto(t)
{
    for (y = [ 0, opto_pitch] )
    {
        translate([ 0, y, 0 ] )
        cube([ opto_dx, opto_dy, t]);
    }
}

    /*
    *
    */

module adc()
{
    translate([ 0, 0, adc_dy ] )
    rotate([ 270, 0, 0 ] )
    {
        cube([ adc_dx, adc_dy, adc_thick, ] );
        translate([ jack_x0, jack_y0, jack_dz ] )
        rotate([ 0, 90, 0 ] )
        cylinder(h=jack_dx, r=jack_r);
    }
}

module adcs()
{
    for (i = [ 0 : 3 ])
    {
        y = i * adc_pitch;
        translate([ 0, y, 0 ] )
        adc();
    }
}

    /*
    *
    */

module boards()
{
    adcs();

    translate([ -5, 70, opto_z0 ])
    opto(10);

    translate([ -4, -40, 20 ])
    rotate([ 90, 0,  90 ] )
    iec_cutout(iec_s3, 20, m3_hole_r);

    translate([ adc_dx - pmod_y0 +2, 5 + (adc_pitch * 4), 0 ] )
    rotate([ 0, 0, 270 ] )
    tang_nano();

    translate([ psu_x0, psu_y0, 0 ] )
    psu();
}

    /*
    *
    */

module bracket()
{
    translate( [ 0, 0, br_t+0.1 ] )
    rotate([ 0, -90, 0 ] )
    difference()
    {
        union()
        {
            cube([ br_h, br_w, br_t ] );
            cube([ br_t, br_w, br_d ] );
        }

        translate([ -0.01, br_w/2, br_t + ((br_d - br_t)/2)])
        rotate([ 0, 90, 0 ] )
        cylinder(h=br_t+0.02, r=br_hole_r);
    }
}

module bracket_base()
{
    rotate([ 0, -90, 0 ] )
    difference()
    {
        cube([ br_t, br_w, br_d ] );

        translate([ -0.01, br_w/2, br_t + ((br_d - br_t)/2)])
        rotate([ 0, 90, 0 ] )
        cylinder(h=br_t+0.02, r=br_thread_r);
    }
}

    /*
    ;
    */

module base_fix()
{
    dx = 10;
    dy = br_w;
    dz = top_fix_z0 + (dx/2);

    difference()
    {
        translate([ -dx/2, 0, 0 ] )
        cube([ dx, dy, dz ]);

        translate( [ 0, -0.01, top_fix_z0 ] )
        rotate([ 270, 0, 0 ] )
        cylinder(h=br_w+0.02, r=top_fix_thread_r);
    }
}

module base()
{
    translate(panel_offset)
    {
        cube([ base_dx, base_dy, base_thick ] );

        // strengthening bars
        w = br_w;
        for (y = br_ys)
        {
            translate([ 0, y, 0 ] )
            {
                cube([ base_dx - br_d + 0.01, w, br_t ]);
                translate([ base_dx, 0, 0 ] )
                bracket_base();
            }
        }

    }

    // psu board mounts
    for (xy = psu_points)
    {
        translate([ xy[0] + psu_x0, xy[1] + psu_y0, -0.01 ])
        difference()
        {
            cylinder(h=psu_z0+0.02, r=psu_thread_r*3);
            cylinder(h=psu_z0+0.02, r=psu_thread_r);
        }
    }

    // side fixing for top section
    translate(panel_offset)
    for (x = top_fix_xs)
    {
        translate( [ x, 0, 0 ] )
        base_fix();
        translate( [ x, top_dy - br_w, 0 ] )
        base_fix();
    }

    difference()
    {
        // back panel
        translate(panel_offset)
        cube([ bp_thick, bp_dy, bp_dz ] );

        #boards();
    }
}

    /*
    *
    */

// rotate around centre
leds_rot = [ 0, 0, 180 ];
leds_mv = [ -led_dx/2, -led_dy/2, 0 ];
leds_back = [ led_dx/2, led_dy/2, 0 ];

module led_strip(thick)
{
    translate(leds_back)
    rotate(leds_rot)
    translate(leds_mv)
    {
        // base pcb
        cube([ led_dx, led_dy, thick ]);

        // led block
        dx = (7 * led_led_pitch) + led_led_dx;
        x0 = (led_dx-dx)/2;
        translate([ x0, led_led_y0, 0 ])
        cube([ dx, led_led_dy, led_thick ]);

        // lumpy components
        component_dy = 3;
        component_y0 = 6;
        translate([ 0, component_y0, 0 ] )
        cube([ led_dx, component_dy, led_component ]);
    }
}

module led_strip_posts(h)
{
    // mounting holes
    translate(leds_back)
    rotate(leds_rot)
    translate(leds_mv)
    {
        hole_dx = (led_dx - led_hole_pitch) / 2;
        points = [
            hole_dx,
            led_dx - hole_dx,
        ];

        for (x = points)
        {
            translate([ x, led_hole_y0, led_thick - h ] )
            cylinder(h = h, r=led_hole_r);
        }
    }
}

    /*
    *
    */

// front panel audio jack
fp_jack_r = 7.7/2;
fp_jack_x0 = 10;
fp_jack_y0 = (bp_dy / 2) - 8;

led_strip_x0 = 1 + ((bp_dz - led_dy) / 2);
led_strip_y0 = bp_dx - 20;
led_recess = -0.4; // thickness of panel for LEDs to shine through

module back_panel()
{
    led_strip_offset = [ led_recess + bp_thick - led_thick, led_strip_y0, led_strip_x0 ];
    led_strip_rot = [ 90, 0, 90 ];

    translate(panel_offset)
    {
        difference()
        {
            cube([ bp_thick, bp_dy, bp_dz ] );

            // mains switch
            translate( [ -0.01, sw_y0, sw_x0 ] )
            cube([ bp_thick+0.02, sw_dy, sw_dx,  ] );

            // rotational encoder
            translate( [ -0.01, rot_y0, rot_x0 ] )
            rotate([ 0, 90, 0 ] )
            cylinder(h=bp_thick+0.02, r=rot_r);

            // LED strip
            translate(led_strip_offset)
            rotate(led_strip_rot)
            #led_strip(2);

            // audio jack
            translate( [ -0.01, fp_jack_y0, fp_jack_x0 ] )
            rotate([ 0, 90, 0 ] )
            cylinder(h=bp_thick+0.02, r=fp_jack_r);
        }

        // LED strip
        translate(led_strip_offset)
        rotate(led_strip_rot)
        {
            led_strip_posts(6);
        }

        for (y = br_ys)
        {
            translate([ 0, y, 0 ] )
            bracket();
        }
    }
}

    /*
    *
    */

module top_rim(dx)
{
    back = dx;
    // rim around front panel
    translate([ back, -top_rim_thick, 0 ] )
    cube( [ top_rim_thick, top_rim_w + top_rim_thick, top_dz ] );
    translate([ back, bp_dy - top_rim_w, 0 ] )
    cube( [ top_rim_thick, top_rim_w + top_rim_thick, top_dz ] );

    translate( [ back, 0, top_dz - top_rim_w - top_thick + 0.01, ] )
    cube( [ top_rim_thick, top_dy, top_rim_w + top_thick ] );
}

module top()
{
    difference()
    {
        union()
        {
            // right side
            translate([ 0, -top_thick, 0 ] )
            cube([ top_dx, top_thick, top_dz ] );
            // left side
            translate([ 0, bp_dy, 0 ] )
            cube([ top_dx, top_thick, top_dz ] );

            // top
            translate([ 0, 0, bp_dz ] )
            cube([ top_dx, top_dy, top_thick ] );

            back =  base_dx + top_rim_thick;
            top_rim(back);
            top_rim(-top_rim_thick);
        }

        for (x = top_fix_xs)
        {
            for (y = [ 0, top_dy + top_thick + 0.01 ] )
            {
                translate( [ x, y, top_fix_z0 ] )
                rotate([ 0, 90, 270 ] )
                cylinder(h=top_thick+0.02, r=top_fix_hole_r);
            }
        }
    }
}

//rotate([ 0, 180, 0 ] )
if (1)
{
    {
        #if (1) 
        translate(panel_offset)
        top();

        if (1) base();

        if (1) 
        //rotate( [ 0, 90, 0 ] )
        translate([ base_dx, 0, 0 ] )
        back_panel();   
    }
}

//  FIN
