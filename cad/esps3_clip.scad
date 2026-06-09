
//  Clip to hold the dead bug ESP32-S3 devkit board in place.
//  This bracket can then be glued to the base.

width = 5.5;
length = 63;
height = 5;
lip = 0.5;
lump = length - 32;
lump_t = 2;

thick = 1.5;
base = thick + 1;

lo = length + (2 * thick);
ho =  height + (2 * thick);

// base
translate([ 0, thick-base, 0 ] )
cube([ lo, base, width] );
// ends
cube([ thick, ho, width ] );
translate([ length + thick, 0, 0 ] )
cube([ thick, ho, width ] );
// lump
translate([ thick - 0.01, thick - 0.01, 0] )
cube([ lump, lump_t, width ] );
// tabs
translate([ 0, height + thick, 0 ] )
cube([ thick + lip, thick, width ] );
translate([ lo - lip - thick, height + thick, 0 ] )
cube([ thick + lip, thick, width ] );

//  FIN
