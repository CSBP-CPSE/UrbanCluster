# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# 01_Urb_Clst_&_Hds_Clst_generation.py
# Created on: 2015-03-24
# By : Olivier Draily, DG REGIO
# Updated on: 2019-23-Jan by Milenko Fadic
# Changes
# Added functions and description to make the code more legible. Each function is separated. The variable names are declared at the beginning. 
# Usage: Modify the local variables in this script and then run it (ArcGIS Desktop and Python must be installed on the computer).
# Description:
# This script produces:
# - A raster of Urban Clusters (URB_CLST_GR) with the total population of each cluster.
#Urban clusters are contiguous cells with a density of at least 300 inhabitants/sq Km and a total population ≥ 5000 inhabitants.
# - A raster of High Density Clusters (HDENS_CLST_GR) with the total population of each cluster. 
# It first selects all grid cells with a density of more than 1500 inhabitants/sqKm.
# The contiguous high-density cells are then clustered and gaps inside them are filled.
# Only the clusters with a minimum population of 50 000 inhabitants are kept.
# Then, small bays in the high-density clusters are smoothed using the majority rule iteratively.
# The majority rule means that if at least five out of the eight cells surrounding a cell belong
# to the same high-density cluster it will be added.
# ---------------------------------------------------------------------------
# Import arcpy module

import arcpy, string, os, sys, traceback, time

#Added by Milenko Fadic-The code uses the following command. 
#Reclassify_sa    -->Reclassify_sa (in_raster, reclass_field, remap, out_raster, missing_values)
#RegionGroup_sa   -->RegionGroup_sa <in_raster> <out_raster> {FOUR | EIGHT} {WITHIN | CROSS} {ADD_LINK | NO_LINK} {excluded_value}
					#Records, for each cell in the output, the identity of the connected region to which it belongs within the Analysis window. A unique number is assigned to each region.
#MajorityFilter_sa-->Replaces cells in a raster based on the majority of their contiguous neighboring cells.
#MosaicToNewRaster_management (input_rasters, output_location, raster_dataset_name_with_extension, {coordinate_system_for_the_raster}, {pixel_type}, {cellsize}, number_of_bands, {mosaic_method}, {mosaic_colormap_mode})
#Buffer_analysis (in_features, out_feature_class, buffer_distance_or_field, {line_side}, {line_end_type}, {dissolve_option}, {dissolve_field}, {method})
#Con_sa <in_conditional_raster> <in_true_raster_or_constant> <out_raster> {in_false_raster_or_constant} {where_clause}--http://webhelp.esri.com/arcgisdesktop/9.2/index.cfm?topicname=con_
#Replaces cells in a raster based on the majority of their contiguous neighboring cells.-->  majoeity filter http://webhelp.esri.com/arcgisdesktop/9.3/index.cfm?TopicName=majority_filter
#Combine_sa mbines multiple rasters so a unique output value is assigned to each unique combination of input values.--http://webhelp.esri.com/arcgisdesktop/9.3/index.cfm?TopicName=combine

def remove_layers():
	#Added by MF. This function removes all the layers from the document. This is required
	#because sometimes the files are locked when in use and thus cannot be overwritten. 
	mxd = arcpy.mapping.MapDocument("CURRENT")
	for df in arcpy.mapping.ListDataFrames(mxd):
		for lyr in arcpy.mapping.ListLayers(mxd, "", df):
			arcpy.mapping.RemoveLayer(df, lyr)

def cleaningProcess():
	# Routines- Remove all files in the current directory 
	print "   Cleaning ..."
	file=os.listdir(arcpy.env.scratchWorkspace)
	for fc in file:
		if arcpy.Exists (fc):
			try:
				arcpy.Delete_management(fc)
			except:
				os.remove(fc)


def mask_cells_more_300(population_Grid):
	#This function classifies creates a mask with group of cells of more than 300 inhabitants/sq Km and a total population ≥ 5000 inhabitants
	#The functions are the reclassify and region group. 
	mask="Mask_D300_GR"	
	print "All grid cells with a density of at least 300 inhabitants/sqKm and a total population >= 5000 inhabitants are kept"
	arcpy.gp.Reclassify_sa(population_Grid, "Value", "0 300 NODATA;300 10000000 1", mask, "DATA")
	arcpy.gp.RegionGroup_sa(mask, "RGGURBCELLSGR", "EIGHT", "WITHIN", "ADD_LINK", "")
	arcpy.gp.ZonalStatistics_sa("RGGURBCELLSGR", "VALUE", population_Grid, "SUMUbClGR5k", "SUM", "DATA")
	#Urban clusters 
	arcpy.gp.Reclassify_sa("SUMUbClGR5k", "VALUE", "0 5000 NODATA", urb_Clst_Grid, "DATA")	
	
def mask_cells_more_1500(population_Grid):
	#This function classifies creates a mask with group of cells of more than 1500 inhabitants/sqKm.
	#The functions are the reclassify and region group. Note that a mask is created with 0 or 1. 
	polygon_output_buffer="CstPl0BPL"
	mask="Mask_D1500_GR"
	input_raster=mask+';'+polygon_output_buffer 
	print "All grid cells with a density of more than 1500 inhabitants/sqKm are kept"
	#Creates the mask. 
	arcpy.gp.Reclassify_sa(population_Grid, "Value", "0 1500 0;1500 1000000 1;NODATA 0", mask , "DATA")

	
def create_constant_poly():
	mask="Mask_D1500_GR"
	constant_raster="dummyraster"
	dummy_polygon="dummy_polygon"
	polygon_output_buffer="CstPl0BPL"
	polygon_output_buffer_ouput="dummy_polbuff.tif"
	input_raster=mask+';'+polygon_output_buffer
	mosaic_result="MaskD1500EGR.tif"
	
	#Settings for process below
	print "RasterToPolygon conversion"
	tempEnvironment0 = arcpy.env.outputCoordinateSystem
	arcpy.env.outputCoordinateSystem = ""
	tempEnvironment1 = arcpy.env.geographicTransformations
	arcpy.env.geographicTransformations = ""
	arcpy.gp.CreateConstantRaster_sa(constant_raster, "0", "INTEGER", mask, mask)
	arcpy.env.outputCoordinateSystem = tempEnvironment0
	arcpy.env.geographicTransformations = tempEnvironment1
	
	#Convert the raster to polygon and add a buffer and then convert it back to raster
	#The purpose is to create an output raster with 0 and 1 denoting the HDCs
	arcpy.RasterToPolygon_conversion(constant_raster, dummy_polygon, "SIMPLIFY", "Value")
	arcpy.Buffer_analysis(dummy_polygon, polygon_output_buffer, "1000 Meters", "FULL", "ROUND", "NONE", "")
	arcpy.PolygonToRaster_conversion(polygon_output_buffer , "gridcode", polygon_output_buffer_ouput , "CELL_CENTER")
	arcpy.Delete_management(polygon_output_buffer)
	arcpy.Delete_management(constant_raster)
	arcpy.Delete_management(dummy_polygon)

	SpatialRef = arcpy.Describe(population_Grid).spatialReference.factoryCode
	#MosaicToNewRaster Merges multiple raster datasets into a new raster dataset.
	#Note that the options in the next command are importnat on which Raster # to take 
	arcpy.MosaicToNewRaster_management(input_raster, output_Workspace, mosaic_result, arcpy.SpatialReference(SpatialRef), "8_BIT_SIGNED", "250", "1", "FIRST", "FIRST")
	print "The output of this command is a polygon grouped "

 
def cluster_hdc():
	#The following function clusters the HDCs together,
	#RDD1 is the group.  
	region_group_mask="RGG1_GR"
	mosaic_result="MaskD1500EGR.tif"
	region_group_reclassified="MaskD1500EGR_fill.tif"
	
	#The commnad below provides a unique ID by different values 
	arcpy.gp.RegionGroup_sa(mosaic_result, region_group_mask, "FOUR", "WITHIN", "NO_LINK", "")
	print "The contiguous high-density cells are clustered"
	arcpy.gp.Reclassify_sa(region_group_mask, "VALUE", "1 0; 2 1000000 1", region_group_reclassified, "DATA")
	arcpy.gp.RegionGroup_sa(region_group_mask, "RGG2_GR", "FOUR", "WITHIN", "NO_LINK", "")
	arcpy.gp.Reclassify_sa(population_Grid, "Value", "0 10000000 0", "Mask_POPL", "DATA")
	#This is a conditional statement, the ones we created are fillers. If the value is >1, meaning a cluster, then group them 
	arcpy.gp.Con_sa("RGG2_GR", "RGG2_GR", "RGG3", "Mask_POPL", "VALUE >1")


def fill_gaps():
	#This function fills in the gaps inside the HDC
	majority_filter_result="MJ_RGG2_GR"
	reclassify_data= "RRGG3_GR"
	input_combine=reclassify_data+";"+majority_filter_result
	output_combine= "D1500sm_GR"
	reclassified_combine="MskD1500fGR"
	hdc_filled_smoothed= "RGG_D1500_GR"
	
	print "and gaps inside them are filled"
	arcpy.gp.MajorityFilter_sa("RGG3", majority_filter_result, "FOUR", "MAJORITY")
	arcpy.gp.Reclassify_sa(majority_filter_result, "VALUE", "0 0;1 10000000 1;NODATA 0",reclassify_data, "DATA")
	arcpy.gp.Combine_sa(input_combine,output_combine)
	arcpy.gp.Reclassify_sa(output_combine, "VALUE", "1 NODATA;2 10000000 1", reclassified_combine, "DATA")
	arcpy.gp.RegionGroup_sa(reclassified_combine, hdc_filled_smoothed, "FOUR", "WITHIN", "NO_LINK", "")
	#End of the process

def keep_cluster_more50k():  
	#This function looks at the clustered HDC and keeps those with +50k population 
	hdc_filled_smoothed= "RGG_D1500_GR" 
	stast_hdc= "SUMD1500sm"
	hdc_mask="HDC_MASK_GR"
	group_hdc= "RegionG_Grid1"
	no_hdc="IsNull_Regio1"
	no_hdc2= "Con_IsNull_R1"
	mask="GPOP_MASK0"
	hdc_out_name="HDCSMR"

	print "Only the clusters with a minimum population of 50 000 inhabitants are kept"
	arcpy.gp.ZonalStatistics_sa(hdc_filled_smoothed, "VALUE", population_Grid, stast_hdc, "SUM", "DATA")
	arcpy.gp.Reclassify_sa(stast_hdc, "VALUE", "0 50000 NODATA;50000 50000000 1", hdc_mask, "DATA")
	arcpy.gp.RegionGroup_sa(hdc_mask, group_hdc, "FOUR", "WITHIN", "ADD_LINK", "")
	arcpy.sa.IsNull(group_hdc).save(no_hdc)
	arcpy.sa.Con(no_hdc, "0",group_hdc, "VALUE =1").save(no_hdc2)
	arcpy.sa.Reclassify(population_Grid, "VALUE", "0 100000 0", "DATA").save(mask)
	arcpy.sa.Plus(no_hdc2,mask).save(hdc_out_name)

	
def smoothing_clusters():
	# Small bays in the high-density clusters are smoothed using the majority rule iteratively.
	# The majority rule means that if at least five out of the eight cells surrounding a cell belong
	# to the same high-density cluster it will be added.
	hdc_out_name="HDCSMR"
	hdc_smoothed="HDCsmooth" 
	hdc_mask="HDC_MASK_GR"
	hdc3="HDC3"
	mask="GPOP_MASK0"
	no_hdc2= "Con_IsNull_R1"
	arcpy.env.workspace = r"V:\Fadic_M\BACKUP\Tunisia\out_data_arcgis"
	print "Create " + os.path.basename(hdens_Clst_Grid) + " by an iterative smoothing process"

	sumDiff = ''
	i = 1
	while sumDiff != 0:
		print " Smooth " + str(i)
		arcpy.gp.MajorityFilter_sa(hdc_out_name, "Majorit_HD_C1", "EIGHT", "MAJORITY")
		arcpy.sa.Reclassify("Majorit_HD_C1", "VALUE", "0 0;1 1000000 1", "DATA").save("Reclass_Majo1")
		arcpy.sa.Reclassify(hdc_out_name, "VALUE", "0 0;1 1000000 1", "DATA").save("Reclass_HD_C1")
		arcpy.sa.Plus("Reclass_Majo1", "Reclass_HD_C1").save("rastercalc")
		arcpy.sa.Reclassify("rastercalc", "VALUE", "0 NODATA;1 2 1", "DATA").save("Reclass_rast1")
		arcpy.sa.RegionGroup("Reclass_rast1", "FOUR", "WITHIN", "ADD_LINK", "").save("RegionG_Recl1")
		arcpy.sa.IsNull("RegionG_Recl1").save("IsNull_Regio1")
		arcpy.sa.Con("IsNull_Regio1", "0", "RegionG_Recl1", "VALUE =1").save("Con_IsNull_R1")
		arcpy.sa.Plus(mask, "Con_IsNull_R1").save(hdc_smoothed)
		arcpy.sa.Minus(hdc_smoothed, hdc_out_name).save("rastercalc1")
		print "  Checking the result"
		arcpy.sa.ZonalStatisticsAsTable(hdc_mask, "Value", "rastercalc1", "DIFF_RST_STATS_TEMP", "DATA", "SUM")
		cur = arcpy.SearchCursor("DIFF_RST_STATS_TEMP")
		for row in cur:
			sumDiff = int(row.getValue("SUM"))
		del cur, row
		print "Renaming"
		arcpy.Delete_management(hdc_out_name)
		print "Deleted"
		arcpy.Rename_management(hdc_smoothed, hdc_out_name)
		i = i + 1
		print "New Loop"
		

def finalize_raster():
	hdc_out_name="HDCSMR"
	reclassname="mcpgr"
	final="RG_POPL"
				
	print "Adding population figures..."
	arcpy.gp.Reclassify_sa  (hdc_out_name, "Value", "0 NODATA;1 90000 1", reclassname, "DATA")
	arcpy.gp.RegionGroup_sa (reclassname, final,  "EIGHT", "WITHIN", "ADD_LINK", "")
	arcpy.gp.ZonalStatistics_sa(final, "VALUE", population_Grid, hdens_Clst_Grid, "SUM", "DATA")


def convert_raster_2_polygon():
	output_urb=r"V:"
	output_hdc=r"V:"
	arcpy.RasterToPolygon_conversion(urb_Clst_Grid, output_urb, "NO_SIMPLIFY", "VALUE")
	arcpy.RasterToPolygon_conversion(hdens_Clst_Grid, output_hdc, "NO_SIMPLIFY", "VALUE")
	


# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")

# Local variables:
population_Grid = r"..\ghs_2015_1km.tif"  
output_Workspace =r"G:\Test"
arcpy.env.workspace =output_Workspace
arcpy.env.scratchWorkspace =r"G:\Test.gbd"
urb_Clst_Grid = output_Workspace + "\\" + "URB_CLST_GR"
hdens_Clst_Grid = output_Workspace + "\\" + "HDENS_CLST_GR"

# Set environment parameters
arcpy.env.overwriteOutput = True


#Starting the process 
if __name__ == "__main__":
	print "Starting" + time.strftime("%H:%M:%S", time.localtime())          
	cleaningProcess()
	mask_cells_more_300(population_Grid)
	mask_cells_more_1500(population_Grid)
	create_constant_poly()
	cluster_hdc()
	fill_gaps()
	keep_cluster_more50k()
	smoothing_clusters()
	finalize_raster()
	convert_raster_2_polygon()
	print "End: " + time.strftime("%H:%M:%S", time.localtime())          
	


