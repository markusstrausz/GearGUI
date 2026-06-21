use <C:/Users/marku/OneDrive/Dokumente/python/Zahnrad3/gears-master/gears.scad>;
m=1.0; z1=30; z2=11; ang=90; tw=8; d1=5; d2=4; pa=20; ha=0;
r_gear_tmp = m*z1/2;
delta_gear_tmp = atan(sin(ang)/(z2/z1+cos(ang)));
delta_pinion_tmp = atan(sin(ang)/(z1/z2+cos(ang)));
rg_tmp = r_gear_tmp/sin(delta_gear_tmp);
c_tmp = m/6;
df_pinion_tmp = pi*rg_tmp*delta_pinion_tmp/90 - 2 * (m + c_tmp);
rf_pinion_tmp = df_pinion_tmp/2;
delta_f_pinion_tmp = rf_pinion_tmp/(pi*rg_tmp) * 180;
height_f_pinion_tmp = rg_tmp*cos(delta_f_pinion_tmp);
df_gear_tmp = pi*rg_tmp*delta_gear_tmp/90 - 2 * (m + c_tmp);
rf_gear_tmp = df_gear_tmp/2;
delta_f_gear_tmp = rf_gear_tmp/(pi*rg_tmp) * 180;
height_f_gear_tmp = rg_tmp*cos(delta_f_gear_tmp);
rotate([0,0,45]) bevel_gear(m,z1,delta_gear_tmp,tw,d1,pa,ha);
translate([-height_f_pinion_tmp*cos(90-ang),0,height_f_gear_tmp-height_f_pinion_tmp*sin(90-ang)])
rotate([0,ang,0]) rotate([0,0,-122.7272727]) bevel_gear(m,z2,delta_pinion_tmp,tw,d2,pa,-ha);
