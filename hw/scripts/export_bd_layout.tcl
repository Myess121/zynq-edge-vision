# Export block design diagrams of edge_v1 / edge_v2 for the documentation
set out E:/project/fpga/work/docs/figures
file mkdir $out
foreach {name xpr} [list edge_v1 E:/project/fpga/work/edge_v1/edge_v1.xpr edge_v2 E:/project/fpga/work/edge_v2/edge_v2.xpr] {
    open_project $xpr
    open_bd_design [get_files base.bd]
    write_bd_layout -force -format pdf -orientation landscape -file $out/${name}_bd.pdf
    write_bd_layout -force -format svg -file $out/${name}_bd.svg
    close_project
}
puts DONE
exit
