import arcgisscripting, sys, math, os, tempfile, locale
gp = arcgisscripting.create(9.3)

#directory_name="mezivystupy_connectivity"
#current_folder = os.path.dirname(os.path.realpath(__file__))
#file_folder = os.path.join(current_folder, directory_name)


#if not os.path.exists(file_folder):
#    os.makedirs(os.path.join(current_folder, directory_name))

directory_name=tempfile.mkdtemp()

gp.workspace= directory_name
gp.overwriteoutput=1
gp.toolbox = "management", "analysis", "stat"

#Input
#-----
inobv_w=gp.GetParameterAsText(0)
inline_h=gp.GetParameterAsText(1)
linefld=gp.GetParameterAsText(2)
val_h=gp.GetParameterAsText(3)
inlu=gp.GetParameterAsText(4)
lufld=gp.GetParameterAsText(5)   # landuse class field
val_ws=gp.GetParameterAsText(6) # landuse value W = water
ri=gp.GetParameter(7)  # distance merging near crossing

r=ri/2
val_w=val_ws.upper()
lu_water="lu_water.shp"
inobv="inobv.shp"
inline="streets.shp"
vert="vert.shp"
outpnt="outpnt.shp"
cross="cross.shp"

#Check if inputs are corect
#--------------------------
gp.addmessage("Check if inputs are corect")
#0
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in first parametr."
description = gp.describe(inobv_w)
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#1
msg= "This tool was designed to work with Polyline Feature Classes... Please set Polyline feature class in second parametr."
description = gp.describe(inline_h)
if description.ShapeType<>"Polyline":
    raise gp.adderror(msg)
#2
#3
#4
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in fifth parametr."
description = gp.describe(inlu)
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#5
#6
#7

#Calculating id-key in input layer of urban areas
#------------------------------------------------
gp.addmessage("Calculating id-key in input layer of urban areas")
gp.addfield (inobv_w, "idplgfld", "short")
rows = gp.UpdateCursor(inobv_w) 
row = rows.Next()
i=1
while row:
    row.setvalue("idplgfld",i)
    rows.UpdateRow(row)
    i=i+1
    row = rows.Next()
del row, rows

#Erase highways and city passes from street network
#--------------------------------------------------
gp.addmessage("Erase highways from street network layer")
query=str(linefld)+"<>'"+str(val_h)+"'"
gp.select_analysis(inline_h, inline, query)

#Erase water bodies from layer of urban areas
#--------------------------------------------
gp.addmessage("Erase water bodies from layer of urban areas")

inobv_aw="inobv_aw.shp"

query=str(lufld)+"='"+str(val_w)+"'"
gp.select_analysis(inlu, lu_water, query)
gp.union_analysis([inobv_w,lu_water],"Data.gdb/inobv_aw","ALL")

gp.makefeaturelayer(lu_water,"lyr_w")
gp.makefeaturelayer("Data.gdb/inobv_aw","lyr_obv")
gp.SelectLayerByLocation("lyr_obv", "CONTAINED_BY", "lyr_w")
gp.deleterows("lyr_obv")
gp.delete_management(lu_water)

gp.dissolve_management("Data.gdb/inobv_aw", "Data.gdb/inobv", "idplgfld")
gp.delete_management("Data.gdb/inobv_aw")


gp.CopyFeatures("Data.gdb/inobv", inobv)



#Calculating area in polygon layer of urban areas without water bodies
#---------------------------------------------------------------------
gp.addmessage("Calculating area in polygon layer of urban areas without water bodies")
gp.addfield (inobv, "area", "double")
desc = gp.Describe(inobv)
shapefieldname = desc.ShapeFieldName
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    geometry = row.GetValue(shapefieldname)
    thearea=geometry.area
    row.setvalue("area",thearea)
    rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#----------------------------------
#Begin of calculating valence field
gp.addmessage("Begin of calculating valence field")
#----------------------------------

#Make layer of vertexes
#----------------------
gp.addmessage("Make layer of vertexes")
desc=gp.Describe(inline)
shapefieldname = desc.ShapeFieldName
thesr=desc.SpatialReference
gp.CreateFeatureClass(gp.workspace,vert, "Point","", "ENABLED", "DISABLED", thesr)
gp.addfield(vert, "valence", "short")
listk=[]
rows=gp.SearchCursor(inline) 
row = rows.Next()
while row:
    feat = row.GetValue(shapefieldname)
    partnum=0
    partcount=feat.PartCount
    print partcount
    while partnum < partcount:
        part = feat.GetPart(partnum)
        pnt = part.Next()
        pntcount = 0
        thex=pnt.x
        they=pnt.y
        thekey=(thex*1000000)+they
        while pnt:
            if thekey not in listk:
                cur = gp.InsertCursor(vert)
                rowvert = cur.NewRow()
                rowvert.shape = pnt
                cur.InsertRow(rowvert)
                listk.append(thekey)
            pnt = part.Next()
            pntcount += 1
        partnum += 1
    row=rows.next()
del row, rows, cur

#Wrap-lines around vertexes
#--------------------------
gp.addmessage("Wrap-lines around vertexes")
d=0.01
desc = gp.Describe(vert)
shapefieldname = desc.ShapeFieldName
wrline="wrline.shp"
gp.CreateFeatureClass(gp.workspace, wrline, "Polyline", "", "ENABLED", "DISABLED", thesr)
curwr = gp.InsertCursor(wrline)
lineArray = gp.CreateObject("Array")
rows = gp.SearchCursor(vert) 
row = rows.Next()
while row:
    thefid=row.getvalue("FID")
    feat = row.GetValue(shapefieldname)
    pnt = feat.GetPart()
    thex=pnt.x
    they=pnt.y
    print thex, they
    
    pnta = gp.CreateObject("Point")
    pntb = gp.CreateObject("Point")
    pntc = gp.CreateObject("Point")
    
    pnta.x=thex-(2*d)
    pnta.y=they-d
    pntb.x=thex+(2*d)
    pntb.y=they-d
    pntc.x=thex
    pntc.y=they+(2*d)
    
    lineArray.add(pnta)
    lineArray.add(pntb)
    lineArray.add(pntc)
    lineArray.add(pnta)
    featwr = curwr.NewRow()
    featwr.shape = lineArray
    curwr.InsertRow(featwr)
    featwr.setvalue("ID",thefid)
    
    lineArray.RemoveAll()
    row=rows.next()
del rows, row, curwr

itspnt="itspnt.shp"
singlpnt="singlpnt.shp"
gp.intersect_analysis(wrline + ";" + inline,itspnt,"ALL","","POINT")
gp.MultipartToSinglepart_management(itspnt,singlpnt)

#Use select by atribute to calculate Valence
#-------------------------------------------
gp.addmessage("Use select by atribute to calculate valence field")
rows = gp.UpdateCursor(vert) 
row = rows.Next()
while row:
    thefid=row.getvalue("FID")
    gp.MakeFeatureLayer(singlpnt,"lyr")
    query='FID_wrline='+str(thefid)
    gp.SelectLayerByAttribute("lyr", "NEW_SELECTION", query)
    result=gp.GetCount_management("lyr")
    num=int(result.GetOutput(0))
    print thefid, num
    row.setvalue("valence",num)
    rows.updaterow(row)
    row=rows.next()
del rows, row

#Delete vertexes with low Valence
#--------------------------------
gp.addmessage("Delete vertexes with low Valence")
gp.MakeFeatureLayer(vert,"lyr")
query='valence=0 or valence=1 or valence=2'
gp.SelectLayerByAttribute("lyr", "NEW_SELECTION", query)
gp.deleterows("lyr")
gp.delete("itspnt.shp")
gp.delete("singlpnt.shp")
gp.delete("wrline.shp")
#---------------------------------
#End of calculatting valence field
gp.addmessage("End of calculatting valence field")
#---------------------------------

#---------------------------------------
#Begin of generalization of near crosses
gp.addmessage("Begin of generalization of near crosses")
#---------------------------------------

#Make buffer zones round crossings and compare their areas
#---------------------------------------------------------
gp.addmessage("Make buffer zones round crossings and compare their areas")
gp.buffer_analysis(vert, "buf.shp", r, "FULL", "#", "ALL")
gp.MultipartToSinglepart_management("buf.shp","buf_singl.shp")
gp.delete_management("buf.shp")
gp.addfield_management("buf_singl.shp", "area", "double")

desc = gp.Describe("buf_singl.shp")
shapefieldname = desc.ShapeFieldName
rows = gp.UpdateCursor("buf_singl.shp") 
row = rows.Next()
while row:
    geometry=row.GetValue(shapefieldname)
    thearea=geometry.area
    row.setvalue("area",thearea)
    rows.UpdateRow(row)
    row = rows.Next()
del row, rows

gp.MakeFeatureLayer("buf_singl.shp","lyr")
thearea=(math.pi)*(math.pow(r,2))
query='AREA<'+str(thearea)
print query
gp.SelectLayerByAttribute("lyr", "NEW_SELECTION", query)
gp.deleterows("lyr")
gp.makefeaturelayer("buf_singl.shp","lyr_ba")
gp.makefeaturelayer("vert.shp","lyr_vert")
gp.SelectLayerByLocation("lyr_vert", "within", "lyr_ba")
gp.deleterows("lyr_vert")

#Make center-points from polygons
#--------------------------------
gp.addmessage("Make center-points from polygons")
print "create center point from polygon"
gp.CreateFeatureClass(gp.workspace, "centroid.shp", "Point", "", "ENABLED", "DISABLED", thesr)
gp.addfield("centroid.shp", "valence", "short")
cur_cent=gp.InsertCursor("centroid.shp")
desc = gp.Describe("buf_singl.shp")
shapefieldname = desc.ShapeFieldName
rows = gp.SearchCursor("buf_singl.shp") 
row = rows.Next()
while row:
    k=0
    sumx=0
    sumy=0
    # Create the geometry object
    feat = row.GetValue(shapefieldname)
    partnum = 0
    partcount = feat.PartCount
    while partnum < partcount:
        # Print the part number
        print "Part " + str(partnum) + ":"
        part = feat.GetPart(partnum)
        pnt = part.Next()
        pntcount = 0
        while pnt:
            sumx=sumx+pnt.x
            sumy=sumy+pnt.y
            k=k+1
            pnt = part.Next()
            pntcount += 1
            # If pnt is null, either the part is finished or there is an 
            #   interior ring
            if not pnt: 
                pnt = part.Next()
        partnum += 1
    pnt=gp.CreateObject("Point")
    pnt.x=sumx/k
    pnt.y=sumy/k
    feat=cur_cent.NewRow()
    feat.shape=pnt
    feat.setvalue("valence","4")
    cur_cent.InsertRow(feat)
    lineArray.RemoveAll()
    row = rows.Next()
del row, rows, cur_cent
gp.delete_management("buf_singl.shp")
#-------------------------------------
#End of generalization of near crosses
gp.addmessage("End of generalization of near crosses")
#-------------------------------------

#Make final layer of crossings
#-----------------------------
gp.addmessage("Make finall layer of crosses")
gp.Merge_management("centroid.shp"+";"+"vert.shp", cross)
gp.delete_management("centroid.shp")
gp.delete_management("vert.shp")
gp.delete_management(inline)

#Calculating Connectivity index
#------------------------------
gp.addmessage("Calculating Connectivity index")
gp.addfield (inobv, "area", "double")
gp.SpatialJoin (cross, inobv, "spjoin.shp", "JOIN_ONE_TO_MANY", "KEEP_ALL", "","INTERSECTS")
sezid=[]
sezval=[]
rows = gp.searchCursor("spjoin.shp") 
row = rows.Next()
while row:
    idplg=row.getvalue("idplgfld")
    valval=row.getvalue("valence")
    if not idplg in sezid:
        sezid.append(idplg)
        sezval.append(valval)
    else:
        order=sezid.index(idplg)
        sezval[order]=sezval[order]+valval
        print sezval[order]
    row = rows.Next()
del rows, row
print sezid
print sezval

gp.addfield (inobv, "cross_num", "short")
hustkrizfld="hustkriz"
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    idplg=row.getvalue("idplgfld")
    print idplg
    if idplg in sezid:
        order=sezid.index(idplg)
        y=sezval[order]
        gp.addmessage("Intersection count for id " + str(idplg) + " is " + str(y))
        row.setvalue("cross_num",y)
    else:
        row.setvalue("cross_num","0")
    rows.UpdateRow(row)
    row = rows.Next()    
del rows, row
gp.addfield (inobv, "cross", "double")
gp.CalculateField_management(inobv,"cross","[cross_num] / [area]")

#Copy final values of Connectivity index to input layer of urban areas
#---------------------------------------------------------------------
gp.addmessage("Copy final values of Connectivity index to input layer of urban areas")
sezid=[]
sezcr=[]
rows = gp.searchCursor(inobv) 
row = rows.Next()
while row:
    idplg=row.getvalue("idplgfld")
    cross=row.getvalue("cross")
    sezid.append(idplg)
    sezcr.append(cross)
    row = rows.Next()
del rows, row

gp.addfield (inobv_w, "cross", "double")
rows = gp.UpdateCursor(inobv_w) 
row = rows.Next()
while row:
    idplg=row.getvalue("idplgfld")
    order=sezid.index(idplg)
    y=sezcr[order]
    row.setvalue("cross",y)
    rows.UpdateRow(row)
    row = rows.Next()
del rows, row

gp.delete_management("spjoin.shp")

#Z-score
#-------
gp.addmessage("Z-score")
gp.Statistics_analysis(inobv_w, "stat.dbf","cross mean; cross std")

rows = gp.SearchCursor("stat.dbf") 
row = rows.Next()

themean=row.GetValue("mean_cross")
thestd=row.GetValue("std_cross")
print themean, thestd
gp.addfield (inobv_w, "cross_z_sc", "double")
rows = gp.UpdateCursor(inobv_w) 
row = rows.Next()
while row:
    thecdens=row.Getvalue("cross")
    if not thestd==0:
        thecdens_st=(thecdens-themean)/thestd
        row.setvalue("cross_z_sc", thecdens_st)
        rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Deciles
#-------
gp.addmessage("Deciles")
list_dec=[]
rows = gp.SearchCursor(inobv_w) 
row = rows.Next()
while row:
    thevalue=row.getvalue("cross_z_sc")
    list_dec.append(thevalue)
    row = rows.Next()
del row, rows

gp.addfield (inobv_w, "cross_dec", "double")
list_dec.sort()
thelen=len(list_dec)
p_dec=thelen/float(10)
print thelen, p_dec
rows = gp.UpdateCursor(inobv_w) 
row = rows.Next()
while row:
    thevalue=row.getvalue("cross_z_sc")
    order=list_dec.index(thevalue)
    k=1
    while 1:
        k_dec=k*p_dec
        print k, k_dec
        if order<k_dec:
            row.setvalue("cross_dec", k)
            rows.UpdateRow(row)
            break
        k=k+1    
    row = rows.Next()
del row, rows

gp.delete_management("stat.dbf")
#gp.deletefield_management(inobv_w, "idplgfld")
gp.delete_management("cross.shp")
gp.delete_management("inobv.shp")
#os.removedirs(directory_name)
gp.workspace=None

gp=None
