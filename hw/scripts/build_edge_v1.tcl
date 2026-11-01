# edge_v1: base design + PL-side OV5640 configuration, without the iop_arduino MicroBlaze subsystem
set src  E:/project/fpga/work/base_2026
set dst  E:/project/fpga/work/edge_v1
set rtl  E:/project/fpga/work/edge_v1_src/rtl

open_project $src/base.xpr
file delete -force $dst
save_project_as edge_v1 $dst -force
add_files -norecurse [glob $rtl/*.v]
update_compile_order -fileset sources_1

open_bd_design [get_files base.bd]

# --- remove iop_arduino and the AXI IIC camera controller -------------------------------
set gone {}
foreach c {iop_arduino cam_iic} {
    if {[llength [get_bd_cells -quiet $c]]} { lappend gone $c }
}
puts "REMOVING: $gone"
delete_bd_objs [get_bd_cells $gone]

# external ports left without any connection
foreach p [get_bd_intf_ports] {
    if {[llength [get_bd_intf_nets -quiet -of_objects $p]] == 0} { puts "drop intf port $p"; delete_bd_objs $p }
}
foreach p [get_bd_ports] {
    if {[llength [get_bd_nets -quiet -of_objects $p]] == 0} { if {![catch {delete_bd_objs $p}]} { puts "drop port $p" } }
}

# --- PL OV5640 configuration (ALIENTEK SCCB state machine) ------------------------------
create_bd_cell -type module -reference ov5640_hw_cfg ov5640_cfg
set ps [get_bd_cells -filter {VLNV =~ "*processing_system7*"}]
puts "PS cell: $ps"
connect_bd_net [get_bd_pins $ps/FCLK_CLK0] [get_bd_pins ov5640_cfg/clk]
connect_bd_net [get_bd_pins rst_ps7_0_fclk0/peripheral_aresetn] [get_bd_pins ov5640_cfg/rst_n]
create_bd_port -dir O cam_scl
create_bd_port -dir IO cam_sda
connect_bd_net [get_bd_ports cam_scl] [get_bd_pins ov5640_cfg/cam_scl]
connect_bd_net [get_bd_ports cam_sda] [get_bd_pins ov5640_cfg/cam_sda]

assign_bd_address
validate_bd_design
save_bd_design

# --- constraints: rename camera SCCB pins, drop pins of removed ports --------------------
set xdc_in  [get_files -of_objects [get_filesets constrs_1] *.xdc]
set fin [open $xdc_in r]; set txt [read $fin]; close $fin
set txt [string map {cam_iic_scl_io cam_scl cam_iic_sda_io cam_sda} $txt]
set keep {}
set ports [concat [get_property NAME [get_bd_ports]] cam_scl cam_sda]
foreach line [split $txt "\n"] {
    if {[regexp {get_ports\s*\{?\s*([A-Za-z0-9_]+)} $line -> pn]} {
        if {[lsearch -exact $ports $pn] < 0 && ![string match *\[* $pn]} {
            set base_pn $pn
            set ok 0
            foreach p $ports { if {[string match "${p}*" $pn]} { set ok 1 } }
            if {!$ok} { append keep "# removed: $line\n"; continue }
        }
    }
    append keep "$line\n"
}
file mkdir $dst/constrs
set fout [open $dst/constrs/edge_v1.xdc w]; puts -nonewline $fout $keep; close $fout
remove_files -fileset constrs_1 $xdc_in
add_files -fileset constrs_1 $dst/constrs/edge_v1.xdc

# --- build -------------------------------------------------------------------------------
set bd [get_files base.bd]
generate_target all $bd
make_wrapper -files $bd -top -force
set_property top base_wrapper [current_fileset]
update_compile_order -fileset sources_1
reset_run synth_1
launch_runs synth_1 -jobs 12
wait_on_run synth_1
puts "SYNTH_STATUS: [get_property STATUS [get_runs synth_1]]"
launch_runs impl_1 -to_step write_bitstream -jobs 12
wait_on_run impl_1
puts "IMPL_STATUS: [get_property STATUS [get_runs impl_1]]"

open_run impl_1
file mkdir $dst/out
report_utilization -file $dst/out/util.txt
report_timing_summary -file $dst/out/timing.txt
file copy -force [glob $dst/edge_v1.runs/impl_1/*.bit] $dst/out/edge_v1.bit
file copy -force [lindex [glob $dst/edge_v1.gen/sources_1/bd/base/hw_handoff/*.hwh] 0] $dst/out/edge_v1.hwh
write_bd_tcl -force $dst/out/edge_v1_bd.tcl
puts "DONE"
