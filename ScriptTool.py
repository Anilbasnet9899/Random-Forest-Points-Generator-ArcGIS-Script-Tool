"""
Script Name: Random Sampling Locations Script Tool 
Author: Anil Basnet
Course: GEOG 567
Date: 2025-12-16

Purpose:
This script tool generates random UTM sampling locations inside suitable forest habitat
within a user-specified study region. A location is considered suitable only if:
    1) It falls inside forested AVI polygons (Species 1 Percent > 0),
    2) It has slope less than 5 degrees (derived from the DEM),
    3) It is within 1000 meters of an existing road.

Inputs (Tool Parameters):
- Study region polygon (feature class)
- AVI vegetation polygons (feature class)
- DEM raster (raster dataset)
- Roads (feature class)
- Number of random points to generate

Outputs:
- A point feature class named 'Random_Points_Final' saved to the project's Default GDB.
- The output is automatically added to the active map and moved to the top.

Notes (how I wrote it):
- I create intermediate datasets in the scratch geodatabase to avoid cluttering the project.
- I use try/except blocks for error handling and messages/progressor for user feedback.
- I check schema locks before overwriting the final output feature class.

"""
import arcpy
from arcpy.sa import*
import os
import random as rd

# Get Default Geodatabase (ArcGIS Pro)
aprx = arcpy.mp.ArcGISProject("CURRENT")
default_gdb = aprx.defaultGeodatabase


try:
    # Check if Spatial Analyst is available
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        arcpy.AddMessage("Spatial Analyst extension checked out successfully.")
    else:
        raise arcpy.ExecuteError("Spatial Analyst extension is not available.")

except arcpy.ExecuteError:
    arcpy.AddError("ArcPy error while checking out Spatial Analyst.")
    arcpy.AddError(arcpy.GetMessages(2))
    raise

except Exception as e:
    arcpy.AddError(f"Unexpected error: {e}")
    raise


arcpy.env.overwriteOutput=True
scratch_gdb=arcpy.env.scratchGDB
arcpy.env.workspace=scratch_gdb 
# Progressor setup
arcpy.SetProgressor("step","Initializing processing...",0, 6, 1)


study_area=arcpy.GetParameterAsText(0)
vegetation=arcpy.GetParameterAsText(1)
dem=arcpy.GetParameterAsText(2)
roads=arcpy.GetParameterAsText(3)
num=int(arcpy.GetParameterAsText(4))

#Create an intermediate empty list that stores the intermediate files inside scratch gdb
intermediate_items = []

#Create a Target Spatial Reference System (WKID= 3400)
target_sr=arcpy.SpatialReference(3400)

#Create a cell size of dem used 
desc_dem=arcpy.Describe(dem)
cell_size=desc_dem.meanCellWidth

#Function that prepares the required Study Area
def prep_studyarea(study_areapath):
    desc=arcpy.Describe(study_areapath)
    if desc.spatialReference.factoryCode != 3400:
        studyarea_proj=arcpy.CreateUniqueName("study_proj", scratch_gdb)
        arcpy.Project_management(study_areapath,studyarea_proj,target_sr)
        intermediate_items.append(studyarea_proj)
        return studyarea_proj
    else:
        return study_areapath 
   

#Create a function that prepares roads criteria
def process_roads(roads_path,studyarea):
    desc=arcpy.Describe(roads_path)
    roads_proj=arcpy.CreateUniqueName("roads_proj", scratch_gdb)
    if desc.spatialReference.factoryCode!=3400:
        arcpy.Project_management(roads_path,roads_proj,target_sr)
        intermediate_items.append(roads_proj)
        roadproj=roads_proj
    else:
        roadproj=roads_path

    roads_clip=arcpy.CreateUniqueName("roads_clip", scratch_gdb)
    arcpy.Clip_analysis(roadproj,studyarea,roads_clip)
    intermediate_items.append(roads_clip)
    roads_buffer = arcpy.CreateUniqueName("roads_buffer", scratch_gdb)

    arcpy.Buffer_analysis(roads_clip,roads_buffer,'1000 Meters',dissolve_option='ALL')
    intermediate_items.append(roads_buffer)
    roads_raster=arcpy.CreateUniqueName("roads_raster", scratch_gdb)
    arcpy.PolygonToRaster_conversion(roads_buffer,'OBJECTID',roads_raster,cellsize=cell_size)
    intermediate_items.append(roads_raster)
    roads_binary= Con(IsNull(roads_raster),0,1)
    roads_binary_raster=arcpy.CreateUniqueName("roads_binary", scratch_gdb)
    intermediate_items.append(roads_binary_raster)
    roads_binary.save(roads_binary_raster)
    return roads_binary_raster


#Create a function that prepares forest criteria
def process_vegetation(vegetation_path,studyarea):
   desc=arcpy.Describe(vegetation_path)
   vegetation_proj=arcpy.CreateUniqueName("vegetation_proj", scratch_gdb)
   if desc.spatialReference.factoryCode!=3400:
        arcpy.Project_management(vegetation_path,vegetation_proj,target_sr)
        intermediate_items.append(vegetation_proj)
        vegetationproj=vegetation_proj
   else:
       vegetationproj=vegetation_path
   vegetation_clip=arcpy.CreateUniqueName("vegetation_clip", scratch_gdb)
   arcpy.Clip_analysis(vegetationproj,studyarea,vegetation_clip)
   intermediate_items.append(vegetation_clip)
   veg_raster=arcpy.CreateUniqueName("veg_raster", scratch_gdb)
   arcpy.PolygonToRaster_conversion(vegetation_clip,'SP1_PER',veg_raster,cellsize=cell_size)
   intermediate_items.append(veg_raster)
   forest_binary=Con(Raster(veg_raster)>0,1,0)
   forest_binary_raster=arcpy.CreateUniqueName("forest_binary_raster", scratch_gdb)
   intermediate_items.append(forest_binary_raster)
   forest_binary.save(forest_binary_raster)
   return forest_binary_raster


#Create a function that prepares slope criteria
def process_slope(dem_path,studyarea):
    desc=arcpy.Describe(dem_path)
    dem_proj=arcpy.CreateUniqueName("dem_proj", scratch_gdb)
    if desc.spatialReference.factoryCode !=3400:
        arcpy.ProjectRaster_management(dem_path,dem_proj,target_sr,resampling_type='BILINEAR')
        intermediate_items.append(dem_proj)
        demproj=dem_proj
    else:
        demproj=dem_path
    #Set raster envs to the DEM you will actually use
    arcpy.env.snapRaster = demproj
    arcpy.env.cellSize = demproj
    arcpy.env.extent = study_area

    dem_clip=arcpy.CreateUniqueName("dem_clip", scratch_gdb)
    out_raster=ExtractByMask(demproj,studyarea)
    out_raster.save(dem_clip)
    intermediate_items.append(dem_clip)
    slope_raster=Slope(dem_clip,output_measurement='DEGREE')
    slope_binary=Con(IsNull(slope_raster),0,Con(slope_raster<5,1,0))
    slope=arcpy.CreateUniqueName("slope", scratch_gdb)
    intermediate_items.append(slope)
    slope_binary.save(slope)
    return slope
#Create a function that returns the count
def get_count(fc):
    return int(arcpy.GetCount_management(fc)[0])

#Test whether schema is locked or not.
def ensure_no_lock(dataset):
    if not arcpy.Exists(dataset):
        return
    if not arcpy.TestSchemaLock(dataset):
        arcpy.AddError(f"Schema lock detected on dataset: {dataset}. Close ArcGIS Pro tables/layers using it.")
        raise arcpy.ExecuteError

study_area_fc=prep_studyarea(study_area)

arcpy.SetProgressorLabel("Preparing road criteria...")
arcpy.SetProgressorPosition()
roads_bin=process_roads(roads,study_area_fc)

arcpy.SetProgressorLabel("Preparing Forest criteria...")
arcpy.SetProgressorPosition()
forest_bin=process_vegetation(vegetation,study_area_fc)

arcpy.SetProgressorLabel("Preparing slope criteria...")
arcpy.SetProgressorPosition()
slope_bin=process_slope(dem,study_area_fc)

arcpy.SetProgressorLabel("Generating suitability surface...")
arcpy.SetProgressorPosition()

# Combine all binary suitability rasters
suitability=Raster(slope_bin)*Raster(roads_bin)*Raster(forest_bin)
suitable_only = Con(suitability == 1, 1)
suitable_areas=arcpy.CreateUniqueName("suitable_areas", scratch_gdb)
intermediate_items.append(suitable_areas)
suitable_only.save(suitable_areas)

#Convert suitable raster to polygon

suitable_poly=arcpy.CreateUniqueName("suitable_poly", scratch_gdb)
arcpy.RasterToPolygon_conversion(suitable_areas,suitable_poly,simplify='NO_SIMPLIFY',raster_field='VALUE')
intermediate_items.append(suitable_poly)
suitable_poly_dis=arcpy.CreateUniqueName('suitable_poly_dissolve', scratch_gdb)

#Dissolve the suitability polygon
arcpy.Dissolve_management(suitable_poly,suitable_poly_dis)
intermediate_items.append(suitable_poly_dis)

#Create feature class called final points
final_points=arcpy.CreateFeatureclass_management(scratch_gdb,out_name='Random_Points',geometry_type='POINT',spatial_reference=target_sr)

# Add suitability indicator fields to FINAL output
arcpy.AddField_management(final_points, "Road", "SHORT")
arcpy.AddField_management(final_points, "Forest", "SHORT")
arcpy.AddField_management(final_points, "Slope", "SHORT")

intermediate_items.append(final_points)

#Loop until we get the required random validation points

i=0
max_i=50

while get_count(final_points)<num and i<max_i:
    i+=1
    
    remaining=num-get_count(final_points)
    batch=max(remaining*2,200)

    #Create Candidate points that can be used to store the random points generated without testing the suitability criteria for all the binary rasters

    cand_fc=f'cand_pts_{i}'
    if arcpy.Exists(cand_fc):
        arcpy.Delete_management(cand_fc)
    
    #Create a random points from the suitability polygon
    arcpy.CreateRandomPoints_management(scratch_gdb,cand_fc,constraining_feature_class=suitable_poly_dis,number_of_points_or_field=batch)

    #Extract 0,1 binary values to the candidate random points
    ExtractMultiValuesToPoints(cand_fc,[[roads_bin,'Road'],[forest_bin,'Forest'],[slope_bin,'Slope']])

    #Select only those points which meets all the criteria (slope, roads, vegetation)
    arcpy.MakeFeatureLayer_management(cand_fc,'cand_lyr')
    arcpy.SelectLayerByAttribute_management('cand_lyr',where_clause='Slope=1 AND Road=1 AND Forest=1')

    #Append Selected Points to the final points
    arcpy.Append_management('cand_lyr',final_points,'NO_TEST')

    #Clean up
    arcpy.Delete_management('cand_lyr')
    arcpy.Delete_management(cand_fc)

final_count=get_count(final_points)


if final_count == num:

    # Overwrite final_points with the trimmed selection
    trimmed_fc = os.path.join(default_gdb, "Random_Points_Final")

    #Check whether the lock is detected or not
    ensure_no_lock(trimmed_fc)
    
    if arcpy.Exists(trimmed_fc):
        arcpy.management.Delete(trimmed_fc)
    arcpy.management.CopyFeatures(final_points, trimmed_fc)
    arcpy.AddMessage('The final random points layer is created successfully')

    
    # Add final output to map
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        if m:
            m.addDataFromPath(trimmed_fc)
            arcpy.AddMessage("Final random points layer added to the active map.")
    except Exception as e:
        arcpy.AddWarning(f"Could not add output to map: {e}")


if final_count > num:
   
    # Add random field
    if "RandKey" not in [f.name for f in arcpy.ListFields(final_points)]:
        arcpy.AddField_management(final_points, "RandKey", "DOUBLE")
    arcpy.CalculateField_management(final_points, "RandKey", 'random.random()', "PYTHON3",code_block="import random")

    # Sort by random field into a temp FC
    sorted_fc = arcpy.CreateUniqueName("sorted_fc", scratch_gdb)
    if arcpy.Exists(sorted_fc):
        arcpy.Delete_management(sorted_fc)
    arcpy.Sort_management(final_points, sorted_fc, [["RandKey", "ASCENDING"]])

    # Create layer from sorted_fc 
    oid = arcpy.Describe(sorted_fc).OIDFieldName
    arcpy.MakeFeatureLayer_management(sorted_fc, "sorted_lyr")
    arcpy.SelectLayerByAttribute_management("sorted_lyr", "NEW_SELECTION", f"{oid} <= {num}")
    intermediate_items.append(sorted_fc)

    # Overwrite final_points with the trimmed selection
    trimmed_fc = os.path.join(default_gdb, "Random_Points_Final")


    #Check whether the lock is detected or not
    ensure_no_lock(trimmed_fc)
    
    if arcpy.Exists(trimmed_fc):
        arcpy.management.Delete(trimmed_fc)
    arcpy.management.CopyFeatures("sorted_lyr", trimmed_fc)
    arcpy.SetProgressorLabel("Final output created and added to map.")
    arcpy.SetProgressorPosition()

    arcpy.DeleteField_management(trimmed_fc,['RandKey','ORIG_FID'])
    arcpy.AddMessage('The final random points layer is created successfully')

    # Add final output to map
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        if m:
            m.addDataFromPath(trimmed_fc)
            arcpy.AddMessage("Final random points layer added to the active map.")
    except Exception as e:
        arcpy.AddWarning(f"Could not add output to map: {e}")


# CLEAN UP SCRATCH GDB
arcpy.AddMessage("Deleting the intermediate files from scratch geodatabase")
for item in intermediate_items:
    try:
        if arcpy.Exists(item):
            arcpy.Delete_management(item)
    except arcpy.ExecuteError:
        arcpy.AddWarning(f"Could not delete {item}:")
        arcpy.AddWarning(arcpy.GetMessages(2))
arcpy.AddMessage("End of the Script.")
arcpy.ResetProgressor()
arcpy.CheckInExtension("Spatial")









    















        

   
    
       
    
    
        



