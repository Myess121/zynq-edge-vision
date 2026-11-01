# Rebuild PYNQ base design (Vivado 2020.2) in Vivado 2026.1
set src  E:/project/fpga/work/pynq_src
set dst  E:/project/fpga/work/base_2026

file delete -force $dst
create_project base $dst -part xc7z020clg400-2
set_property ip_repo_paths [list $src/ip_repo] [current_project]
update_ip_catalog

set bdsrc E:/project/fpga/work/base_2026_bdsrc
file delete -force $bdsrc
file mkdir $bdsrc
file copy -force $src/base/base.srcs/sources_1/bd/base $bdsrc/base
import_files -norecurse $bdsrc/base/base.bd
add_files -fileset constrs_1 $src/base/base.srcs/constrs_1/new/base.xdc
import_files -fileset constrs_1 -force

set bd [get_files base.bd]
report_ip_status -file $dst/ip_status_before.txt
open_bd_design $bd
upgrade_ip [get_ips] -log $dst/ip_upgrade.log
report_ip_status -file $dst/ip_status_after.txt
validate_bd_design
save_bd_design

generate_target all $bd
make_wrapper -files $bd -top
add_files -norecurse [glob $dst/base.gen/sources_1/bd/base/hdl/base_wrapper.v]
set_property top base_wrapper [current_fileset]
update_compile_order -fileset sources_1

launch_runs synth_1 -jobs 8
wait_on_run synth_1
puts "SYNTH_STATUS: [get_property STATUS [get_runs synth_1]]"
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
puts "IMPL_STATUS: [get_property STATUS [get_runs impl_1]]"

open_run impl_1
report_utilization -file $dst/util.txt
report_timing_summary -file $dst/timing.txt
file mkdir $dst/out
file copy -force [glob $dst/base.runs/impl_1/*.bit] $dst/out/base.bit
file copy -force [glob $dst/base.gen/sources_1/bd/base/hw_handoff/base.hwh] $dst/out/base.hwh
write_bd_tcl -force $dst/out/base.tcl
puts "DONE"
