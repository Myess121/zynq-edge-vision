# Re-run edge_v1 implementation with a timing-driven strategy (base run missed by 33 ps in color_convert)
set dst E:/project/fpga/work/edge_v1
open_project $dst/edge_v1.xpr
set_property strategy Performance_ExplorePostRoutePhysOpt [get_runs impl_1]
reset_run impl_1
launch_runs impl_1 -to_step write_bitstream -jobs 12
wait_on_run impl_1
puts "IMPL_STATUS: [get_property STATUS [get_runs impl_1]]"
open_run impl_1
report_utilization -file $dst/out/util.txt
report_timing_summary -file $dst/out/timing.txt
file copy -force [glob $dst/edge_v1.runs/impl_1/*.bit] $dst/out/edge_v1.bit
file copy -force [lindex [glob $dst/edge_v1.gen/sources_1/bd/base/hw_handoff/*.hwh] 0] $dst/out/edge_v1.hwh
puts "DONE"
