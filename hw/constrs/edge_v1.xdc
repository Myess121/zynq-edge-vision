#HDMI
set_property IOSTANDARD TMDS_33 [get_ports TMDS_clk_p]
set_property IOSTANDARD TMDS_33 [get_ports {TMDS_data_n[0]}]
set_property IOSTANDARD TMDS_33 [get_ports {TMDS_data_n[1]}]
set_property IOSTANDARD TMDS_33 [get_ports {TMDS_data_n[2]}]
set_property -dict { PACKAGE_PIN L19   IOSTANDARD LVCMOS33} [get_ports hdmi_hpd_tri_io]
set_property -dict { PACKAGE_PIN J20   IOSTANDARD TMDS_33 } [get_ports {TMDS_data_p[2]}]
set_property -dict { PACKAGE_PIN K19   IOSTANDARD TMDS_33 } [get_ports {TMDS_data_p[1]}]
set_property -dict { PACKAGE_PIN G19   IOSTANDARD TMDS_33 } [get_ports {TMDS_data_p[0]}]
set_property -dict { PACKAGE_PIN J18   IOSTANDARD TMDS_33 } [get_ports TMDS_clk_p]
# -------------------------GPIO-------------------
#PL_KEY 
set_property -dict { PACKAGE_PIN L14 IOSTANDARD LVCMOS33 } [get_ports { btns_tri_i[0] }]
set_property -dict { PACKAGE_PIN K16 IOSTANDARD LVCMOS33 } [get_ports { btns_tri_i[1] }]
#TPAG 
set_property -dict { PACKAGE_PIN F16 IOSTANDARD LVCMOS33 } [get_ports { touch_tri_i }]
#BEEP  
set_property -dict { PACKAGE_PIN M14 IOSTANDARD LVCMOS33 } [get_ports { beep_tri_o }]
#PL_LED 54-56
set_property -dict { PACKAGE_PIN J16 IOSTANDARD LVCMOS33 } [get_ports { leds_tri_o[0] }]
set_property -dict { PACKAGE_PIN H15 IOSTANDARD LVCMOS33 } [get_ports { leds_tri_o[1] }]
set_property -dict { PACKAGE_PIN L15 IOSTANDARD LVCMOS33 } [get_ports { leds_tri_o[2] }]
#----------------------HDMI DDC---------------------------
set_property -dict { PACKAGE_PIN R19 IOSTANDARD LVCMOS33 } [get_ports { hdmi_ddc_scl_io}]
set_property -dict { PACKAGE_PIN P20 IOSTANDARD LVCMOS33 } [get_ports { hdmi_ddc_sda_io}]  
#----------------------IIC1---------------------------
set_property -dict { PACKAGE_PIN E18 IOSTANDARD LVCMOS33 } [get_ports { IIC_1_scl_io }]
set_property -dict { PACKAGE_PIN F17 IOSTANDARD LVCMOS33 } [get_ports { IIC_1_sda_io }]
#---------------------audio---------------------------
set_property -dict { PACKAGE_PIN M17 IOSTANDARD LVCMOS33 } [get_ports aud_adcdat]
set_property -dict { PACKAGE_PIN L20 IOSTANDARD LVCMOS33 } [get_ports aud_lrc]
set_property -dict { PACKAGE_PIN M18 IOSTANDARD LVCMOS33 } [get_ports aud_bclk]
set_property -dict { PACKAGE_PIN E19 IOSTANDARD LVCMOS33 } [get_ports aud_mclk]
set_property -dict { PACKAGE_PIN G18 IOSTANDARD LVCMOS33 } [get_ports aud_dacdat]

#----------------------camera---------------------------
set_property -dict {PACKAGE_PIN T12 IOSTANDARD LVCMOS33} [get_ports cam_href]
set_property -dict {PACKAGE_PIN W14 IOSTANDARD LVCMOS33} [get_ports cam_pclk]
set_property -dict {PACKAGE_PIN U12 IOSTANDARD LVCMOS33} [get_ports cam_vsync]
set_property -dict {PACKAGE_PIN P14 IOSTANDARD LVCMOS33} [get_ports cam_rst_n]
set_property -dict {PACKAGE_PIN V15 IOSTANDARD LVCMOS33} [get_ports cam_pwdn]

set_property -dict {PACKAGE_PIN R14 IOSTANDARD LVCMOS33} [get_ports {cam_data[0]}]
set_property -dict {PACKAGE_PIN U13 IOSTANDARD LVCMOS33} [get_ports {cam_data[1]}]
set_property -dict {PACKAGE_PIN V13 IOSTANDARD LVCMOS33} [get_ports {cam_data[2]}]
set_property -dict {PACKAGE_PIN U15 IOSTANDARD LVCMOS33} [get_ports {cam_data[3]}]
set_property -dict {PACKAGE_PIN U14 IOSTANDARD LVCMOS33} [get_ports {cam_data[4]}]
set_property -dict {PACKAGE_PIN W13 IOSTANDARD LVCMOS33} [get_ports {cam_data[5]}]
set_property -dict {PACKAGE_PIN V12 IOSTANDARD LVCMOS33} [get_ports {cam_data[6]}]
set_property -dict {PACKAGE_PIN Y14 IOSTANDARD LVCMOS33} [get_ports {cam_data[7]}]

#cam_scl:
set_property -dict {PACKAGE_PIN T10 IOSTANDARD LVCMOS33} [get_ports {cam_scl}]
#cam_sda:
set_property -dict {PACKAGE_PIN T11 IOSTANDARD LVCMOS33} [get_ports {cam_sda}] 
set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets cam_pclk_IBUF]

#----------------------iop_audrino---------------------------
set_property -dict {PACKAGE_PIN V5 IOSTANDARD LVCMOS33} [get_ports {io_0_tri_io[0]}]
set_property -dict {PACKAGE_PIN U7 IOSTANDARD LVCMOS33} [get_ports {io_0_tri_io[1]}]
set_property -dict {PACKAGE_PIN V7 IOSTANDARD LVCMOS33} [get_ports {io_0_tri_io[2]}]
set_property -dict {PACKAGE_PIN T9 IOSTANDARD LVCMOS33} [get_ports {io_0_tri_io[3]}]

set_property -dict {PACKAGE_PIN T19 IOSTANDARD LVCMOS33} [get_ports spi_rtl_0_io0_io]
set_property -dict {PACKAGE_PIN J15 IOSTANDARD LVCMOS33} [get_ports spi_rtl_0_io1_io]
set_property -dict {PACKAGE_PIN G14 IOSTANDARD LVCMOS33} [get_ports spi_rtl_0_sck_io]
set_property -dict {PACKAGE_PIN N15 IOSTANDARD LVCMOS33} [get_ports spi_rtl_0_ss_io ]



