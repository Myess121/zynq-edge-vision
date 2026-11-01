`timescale 1ns / 1ps
// OV5640 power-up register configuration done in PL (replaces the PS-side AXI IIC path).
// Wraps ALIENTEK's i2c_ov5640_rgb565_cfg + i2c_dri: RGB565 output at CMOS_H x CMOS_V.
module ov5640_hw_cfg #(
    parameter CLK_FREQ = 100_000_000,   // clk frequency (Hz)
    parameter I2C_FREQ = 250_000,       // SCCB SCL frequency (Hz)
    parameter CMOS_H   = 640,
    parameter CMOS_V   = 480,
    parameter TOTAL_H  = 1856,          // HTS
    parameter TOTAL_V  = 984            // VTS
)(
    input  wire clk,
    input  wire rst_n,
    output wire cam_scl,
    inout  wire cam_sda,
    output wire init_done
);

wire        i2c_dri_clk;
wire        i2c_done;
wire  [7:0] i2c_data_r;
wire        i2c_exec;
wire [23:0] i2c_data;
wire        i2c_rh_wl;

i2c_ov5640_rgb565_cfg u_i2c_cfg (
    .clk           (i2c_dri_clk),
    .rst_n         (rst_n),
    .i2c_data_r    (i2c_data_r),
    .i2c_done      (i2c_done),
    .cmos_h_pixel  (CMOS_H),
    .cmos_v_pixel  (CMOS_V),
    .total_h_pixel (TOTAL_H),
    .total_v_pixel (TOTAL_V),
    .i2c_exec      (i2c_exec),
    .i2c_data      (i2c_data),
    .i2c_rh_wl     (i2c_rh_wl),
    .init_done     (init_done)
);

i2c_dri #(
    .SLAVE_ADDR (7'h3c),
    .CLK_FREQ   (CLK_FREQ),
    .I2C_FREQ   (I2C_FREQ)
) u_i2c_dri (
    .clk        (clk),
    .rst_n      (rst_n),
    .i2c_exec   (i2c_exec),
    .bit_ctrl   (1'b1),             // 16-bit register address
    .i2c_rh_wl  (i2c_rh_wl),
    .i2c_addr   (i2c_data[23:8]),
    .i2c_data_w (i2c_data[7:0]),
    .i2c_data_r (i2c_data_r),
    .i2c_done   (i2c_done),
    .i2c_ack    (),
    .scl        (cam_scl),
    .sda        (cam_sda),
    .dri_clk    (i2c_dri_clk)
);

endmodule
