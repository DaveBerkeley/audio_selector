
//  cutout 
//  a=height
//  b=width
//  c=hole_spacing
//  d=hole_y
//  e=chamfer_y
//  f=chamfer_x

iec_s1 = [ 18.5+0.5, 26.6+0.5, 40, 9.5, 5.5, 5.5 ];
iec_s2 = [ 25, 32+0.5, 40, 12.2, 7.4, 7.4 ]; // outlet 
iec_s3 = [ 19.6, 27+0.5, 40, 9.5, 5.5, 5.5 ]; // plug Dec-2024
iec_s4 = [ 24, 32, 40, 12.2, 7.4, 7.4 ]; // outlet Dec-2024

function _iec_cutout(params) =
    let (a = params[0])
    let (b = params[1])
    let (c = params[2])
    let (d = params[3])
    let (e = params[4])
    let (f = params[5])
    let (x0 = b/2)
    let (y0 = a/2)
    let (corner = 1.5)

    [
        //[ -x0, -y0 ],
        [ corner-x0, -y0 ],
        [ -x0, corner-y0 ],
        [ -x0, y0-e ],
        [ -x0+f, y0 ],
        [ x0-f, y0 ],
        [ x0, y0-e ],
        [ x0, corner-y0 ],        
        [ x0-corner, -y0 ],        
        [ corner-x0, -y0 ],
    ];

module iec_cutout(params, thick, hole_r)
{
    points = _iec_cutout(params);
    //echo(points);
    linear_extrude(height=thick)
    polygon(points);
    // mounting holes
    c = params[2];
    x0 = c/2;
    translate([-x0, 0, 0])
    cylinder(h=thick, r1=hole_r, r2=hole_r);
    translate([x0, 0, 0])
    cylinder(h=thick, r1=hole_r, r2=hole_r);
}

module test()
{
    $fa = 1;
    $fs = 0.4;

    thick = 1;
    hole_r = 3/2;
    dx = 50;
    dy = 60;
    difference()
    {
        cube([ dx, dy, thick ] );

        translate([ 25, 15, -0.01 ])
        iec_cutout(iec_s4, thick+0.02, hole_r);
        translate([ 25, 45, -0.01 ])
        iec_cutout(iec_s3, thick+0.02, hole_r);
    }
}

//test();

//  FIN
