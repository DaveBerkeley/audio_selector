
//  M3
m3_thread_r = 1.4;
m3_hole_r = 1.8;
m3_head_r = 6.3/2;
m3_csink_r = 5.5/2;

//  M4
m4_thread_r = 1.9;
m4_hole_r = 2.1;
m4_nut_outer_r = 7.7 / 2;
m4_nut_min_r = 6.8 / 2;
m4_csink_r = 7.7/2;
m4_csink_d = 3;

function nut_hexagon(width) =
    // width is the distance between nut faces
    // eg m4_nut_min_r*2
    let (face_len = width / sqrt(3)) // w/tan(30)
    let (F = face_len / 2)
    let (W = width / 2)
    let (outer = sqrt((F * F) + (W * W)))
    [
        [ -F, W ],
        [ F, W ],
        [ outer, 0 ],
        [ F, -W ],
        [ -F, -W ],
        [ -outer, 0 ],
        [ -F, W ],
    ];

//  FIN
