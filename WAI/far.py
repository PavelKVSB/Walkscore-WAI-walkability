import arcgisscripting, sys, math, os, tempfile, locale
gp = arcgisscripting.create(9.3)

#directory_name="mezivystupy_far"
#current_folder = os.path.dirname(os.path.realpath(__file__))
#file_folder = os.path.join(current_folder, directory_name)

#if not os.path.exists(file_folder):
#    os.makedirs(os.path.join(current_folder, directory_name))
    
    
gp.workspace= 'Data.gdb'    #file_folder


gp.overwriteoutput=1
gp.toolbox = "management", "analysis", "stat"

#Input
#-----
gp.addmessage("Input")
inobv=gp.GetParameterAsText(0)
inlu=gp.GetParameterAsText(1)
lufld=gp.GetParameterAsText(2)
thevalue_s=gp.GetParameterAsText(3)
inpnt=gp.GetParameterAsText(4)
areapntfld=gp.GetParameterAsText(5)
buffersize=gp.GetParameterAsText(6)

thevalue=thevalue_s.upper()
itsplg="itsplg"
itspnt="itspnt"

#Check if inputs are corect
#--------------------------
gp.addmessage("Check if inputs are corect")
#0
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in first parametr."
description = gp.describe(inobv)
print description.ShapeType

# Circumference claculation: d = (circumference/pi) / 2 --> only integer
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#1
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in second parametr."
description = gp.describe(inlu)
print description.ShapeType
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#2
#3
#4
msg= "This tool was designed to work with Point Feature Classes... Please set Point feature class in fifth parametr."
description = gp.describe(inpnt)
if description.ShapeType<>"Point":
    raise gp.adderror(msg)
#5
gp.addmessage("Input buffer size: {0}".format(buffersize))

# #Calculating id-key in input layer of urban areas
# #------------------------------------------------
# gp.addmessage("Calculating id-key in input layer of urban areas")
# gp.addfield_management(inobv, "idplgfld", "short")
# i=0
# rows = gp.Updatedescription(inobv)
# row = rows.Next()
# while row:
#     row.setvalue("idplgfld",i)
#     rows.UpdateRow(row)
#     i=i+1
#     rows.UpdateRow(row)
#     row = rows.Next()
# del row, rows

#Intersect input landuse layer and layer of urban areas
#------------------------------------------------------
gp.addmessage("Intersect input landuse and layer of urban areas")
gp.Intersect_analysis([inobv,inlu], itsplg)
fields = gp.ListFields(itsplg)
for field in fields:
    namefld=field.Name
    if namefld=="area":
        gp.deletefield_management(itsplg, "area")
gp.addfield (itsplg, "area", "double")
desc = gp.Describe(itsplg)
shapefieldname = desc.ShapeFieldName

rows = gp.UpdateCursor(itsplg) 
row = rows.Next()
while row:
    geometry = row.GetValue(shapefieldname)
    thearea=geometry.area
    row.setvalue("area",thearea)
    rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Summing areas used for commerce in every urban area (known from polygon layer)
#------------------------------------------------------------------------------
gp.addmessage("Summing areas used for commerce in every urban area (known from polygon layer)")
rows = gp.SearchCursor(itsplg) 
row = rows.Next()
listid=[]
listar=[]
while row:
    theidplg=row.GetValue("idplgfld")
    plocha = row.GetValue("area")
    thelu=row.GetValue(lufld)
    theln=len(thelu)
    area_div=plocha/theln
    for char in thelu:
        if char==thevalue:
            if theidplg not in listid:
                listid.append(theidplg)
                listar.append(area_div)
            else:
                poradi=listid.index(theidplg)
                listar[poradi]=listar[poradi]+area_div
    row = rows.Next()
del row, rows
print listid
print listar

#Filling field by areas used for commerce (known from polygon layer) to input layer of urban areas
#-------------------------------------------------------------------------------------------------
gp.addmessage("Filling field by areas used for commerce (known from polygon layer) to input layer of urban areas")
gp.addfield(inobv, "area_lu", "double")
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    theid=row.getvalue("idplgfld")
    if theid in listid:
        order=listid.index(theid)
        thearea=listar[order]
        row.setvalue("area_lu", thearea)
        rows.UpdateRow(row)
    else:
        row.setvalue("area_lu","0")
        rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Summming areas used for commerce in every urban area (known from point layer)
#-----------------------------------------------------------------------------
gp.addmessage("Summming areas used for commerce in every urban area (known from point layer)")
listid=[]
list_area=[]
gp.intersect_analysis([inpnt,inobv], itspnt, "ALL")
rows = gp.UpdateCursor(itspnt)
row = rows.Next()
while row:
    thearea=row.getvalue(areapntfld)
    theid=row.getvalue("idplgfld")
    if theid not in listid:
        listid.append(theid)
        list_area.append(thearea)
    else:
        order=listid.index(theid)
        list_area[order]=list_area[order]+thearea
    row = rows.Next()
del row, rows

#Filling field by areas used for commerce (known from point layer) to input layer of urban areas
#-----------------------------------------------------------------------------------------------
gp.addmessage("Filling field of areas used for commerce (known from point layer) to input layer of urban areas")
gp.addfield(inobv, "area_obch", "double")
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    theid=row.getvalue("idplgfld")
    if theid in listid:
        order=listid.index(theid)
        print order
        thearea=list_area[order]
        row.setvalue("area_obch", thearea)
        rows.UpdateRow(row)
    else:
        row.setvalue("area_obch","0")
        rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Calculating FAR index

polomer_kruhu = int(buffersize)
#---------------------
gp.addmessage("Calculating FAR index")
gp.addfield (inobv, "far", "double")
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    theareaobch=row.getvalue("area_obch")
    thearealu=row.getvalue("area_lu")
    if thearealu==0:
        row.setvalue("far", "0")
    elif (thearealu/(polomer_kruhu*polomer_kruhu*3.14159265)*100) > 1:
        thefar=theareaobch/thearealu
        row.setvalue("far", thefar)
    else:
        row.setvalue("far", "0")
    rows.UpdateRow(row)
    row=rows.Next()
del row, rows



#Z-score
#-------
gp.addmessage("Z-score")
gp.Statistics_analysis(inobv, "stat.dbf","far mean; far std")
rows = gp.SearchCursor("stat.dbf") 
row = rows.Next()
themean=row.GetValue("mean_far")
thestd=row.GetValue("std_far")
print themean, thestd
gp.addfield (inobv, "far_z_sc", "double")
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    thefar=row.Getvalue("far")
    thefar_st=(thefar-themean)/thestd
    row.setvalue("far_z_sc", thefar_st)
    rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Deciles
#-------
gp.addmessage("Deciles")
list_dec=[]
rows = gp.SearchCursor(inobv) 
row = rows.Next()
while row:
    thevalue=row.getvalue("far_z_sc")
    list_dec.append(thevalue)
    row = rows.Next()
del row, rows

gp.addfield (inobv, "far_dec", "double")
list_dec.sort()
thelen=len(list_dec)
p_dec=thelen/float(10)
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    thevalue=row.getvalue("far_z_sc")
    order=list_dec.index(thevalue)
    k=1
    while 1:
        k_dec=k*p_dec
        if order<k_dec:
            row.setvalue("far_dec", k)
            rows.UpdateRow(row)
            break
        k=k+1    
    row = rows.Next()
del row, rows    

gp.delete_management(itsplg)
gp.delete_management(itspnt)
#gp.deletefield_management(inobv, "idplgfld")
gp.deletefield_management(inobv, "area_lu")
gp.deletefield_management(inobv, "area_obch")
gp.delete_management("stat.dbf")
# os.removedirs(directory_name)
gp=None
 
