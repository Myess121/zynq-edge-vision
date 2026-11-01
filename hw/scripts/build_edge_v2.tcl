# edge_v2: edge_v1 + PL preprocessing (axi_dma on HP1 + resize_accel HLS IP)
set src  E:/project/fpga/work/edge_v1
set dst  E:/project/fpga/work/edge_v2

open_project $src/edge_v1.xpr
file delete -force $dst
save_project_as edge_v2 $dst -force
update_ip_catalog
open_bd_design [get_files base.bd]

set ps  [get_bd_cells -filter {VLNV =~ "*processing_system7*"}]
set clk [get_bd_pins $ps/FCLK_CLK0]
puts "PS cell: $ps"

# HP1 for the preprocessing DMA (HP0 stays with the video VDMA)
set_property -dict [list CONFIG.PCW_USE_S_AXI_HP1 {1} CONFIG.PCW_S_AXI_HP1_DATA_WIDTH {64}] $ps

# DMA (simple mode, 32-bit streams, 26-bit length = up to 64 MB per transfer)
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma axi_dma_0
set_property -dict [list CONFIG.c_include_sg {0} CONFIG.c_sg_length_width {26} \
    CONFIG.c_m_axi_mm2s_data_width {32} CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_m_axi_s2mm_data_width {32} CONFIG.c_s_axis_s2mm_tdata_width {32} \
    CONFIG.c_mm2s_burst_size {256} CONFIG.c_s2mm_burst_size {256}] [get_bd_cells axi_dma_0]

# 32-bit DMA stream <-> 24-bit RGB pixel stream
create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter axis_to_rgb
set_property -dict [list CONFIG.S_TDATA_NUM_BYTES {4} CONFIG.M_TDATA_NUM_BYTES {3} CONFIG.HAS_TLAST {1} CONFIG.HAS_TKEEP {1}] [get_bd_cells axis_to_rgb]
create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter rgb_to_axis
set_property -dict [list CONFIG.S_TDATA_NUM_BYTES {3} CONFIG.M_TDATA_NUM_BYTES {4} CONFIG.HAS_TLAST {1}] [get_bd_cells rgb_to_axis]

# resize HLS IP (bilinear, from the PYNQ resizer example, ip_repo/resize_1.0)
create_bd_cell -type ip -vlnv [lindex [get_ipdefs *resize_accel*] 0] resize_accel_0

connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] [get_bd_intf_pins axis_to_rgb/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins axis_to_rgb/M_AXIS]    [get_bd_intf_pins resize_accel_0/src]
connect_bd_intf_net [get_bd_intf_pins resize_accel_0/dst]    [get_bd_intf_pins rgb_to_axis/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins rgb_to_axis/M_AXIS]    [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

# AXI-Lite control on GP0, DMA masters on HP1
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Master "$ps/M_AXI_GP0" Clk_master Auto Clk_slave Auto Clk_xbar Auto] [get_bd_intf_pins axi_dma_0/S_AXI_LITE]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Master "$ps/M_AXI_GP0" Clk_master Auto Clk_slave Auto Clk_xbar Auto] [get_bd_intf_pins resize_accel_0/s_axi_AXILiteS]
# DMA masters -> HP1 through a dedicated interconnect (bd automation fails on this design)
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect dma_hp1_ic
set_property -dict [list CONFIG.NUM_SI {2} CONFIG.NUM_MI {1}] [get_bd_cells dma_hp1_ic]
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_MM2S] [get_bd_intf_pins dma_hp1_ic/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_S2MM] [get_bd_intf_pins dma_hp1_ic/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins dma_hp1_ic/M00_AXI] [get_bd_intf_pins $ps/S_AXI_HP1]
foreach p {dma_hp1_ic/ACLK dma_hp1_ic/S00_ACLK dma_hp1_ic/S01_ACLK dma_hp1_ic/M00_ACLK axi_dma_0/m_axi_mm2s_aclk axi_dma_0/m_axi_s2mm_aclk} {
    if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins $p]]] == 0} { connect_bd_net $clk [get_bd_pins $p] }
}
connect_bd_net $clk [get_bd_pins $ps/S_AXI_HP1_ACLK]
set icrst [get_bd_pins rst_ps7_0_fclk0/interconnect_aresetn]
if {[llength $icrst] == 0} { set icrst [get_bd_pins rst_ps7_0_fclk0/peripheral_aresetn] }
connect_bd_net $icrst [get_bd_pins dma_hp1_ic/ARESETN]
foreach p {dma_hp1_ic/S00_ARESETN dma_hp1_ic/S01_ARESETN dma_hp1_ic/M00_ARESETN} {
    connect_bd_net [get_bd_pins rst_ps7_0_fclk0/peripheral_aresetn] [get_bd_pins $p]
}

foreach p {axis_to_rgb/aclk rgb_to_axis/aclk resize_accel_0/ap_clk} {
    if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins $p]]] == 0} { connect_bd_net $clk [get_bd_pins $p] }
}
set rstn [get_bd_pins rst_ps7_0_fclk0/peripheral_aresetn]
foreach p {axis_to_rgb/aresetn rgb_to_axis/aresetn resize_accel_0/ap_rst_n} {
    if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins $p]]] == 0} { connect_bd_net $rstn [get_bd_pins $p] }
}

# interrupts -> concat feeding the interrupt controller
set cc [get_bd_cells concat_interrupts]
set n  [get_property CONFIG.NUM_PORTS $cc]
set free {}
for {set i 0} {$i < $n} {incr i} {
    if {[llength [get_bd_nets -quiet -of_objects [get_bd_pins $cc/In$i]]] == 0} { lappend free $i }
}
foreach irq {axi_dma_0/mm2s_introut axi_dma_0/s2mm_introut resize_accel_0/interrupt} {
    if {[llength $free]} {
        set i [lindex $free 0]; set free [lrange $free 1 end]
    } else {
        set i $n; incr n; set_property CONFIG.NUM_PORTS $n $cc
    }
    puts "IRQ $irq -> concat In$i"
    connect_bd_net [get_bd_pins $irq] [get_bd_pins $cc/In$i]
}

assign_bd_address
validate_bd_design
save_bd_design

set bd [get_files base.bd]
generate_target all $bd
make_wrapper -files $bd -top -force
update_compile_order -fileset sources_1
reset_run synth_1
launch_runs synth_1 -jobs 12
wait_on_run synth_1
puts "SYNTH_STATUS: [get_property STATUS [get_runs synth_1]]"
set_property strategy Performance_ExplorePostRoutePhysOpt [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs 12
wait_on_run impl_1
puts "IMPL_STATUS: [get_property STATUS [get_runs impl_1]]"

open_run impl_1
file mkdir $dst/out
report_utilization -file $dst/out/util.txt
report_timing_summary -file $dst/out/timing.txt
file copy -force [glob $dst/edge_v2.runs/impl_1/*.bit] $dst/out/edge_v2.bit
file copy -force [lindex [glob $dst/edge_v2.gen/sources_1/bd/base/hw_handoff/*.hwh] 0] $dst/out/edge_v2.hwh
write_bd_tcl -force $dst/out/edge_v2_bd.tcl
puts "DONE"
