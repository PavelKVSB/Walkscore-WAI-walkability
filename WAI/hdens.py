#------------------------------------
# Name: hdens.py
# Description: Calculate ratio of number of households and areas used for living in every urban area
# Author: Tomas KRIVKA, Department of Geoinformatics, Faculty of Science, Palacky University Olomouc, 2011
#------------------------------------

#Import modules, make geoprocesor, set workspace...
#--------------------------------------------------
import arcgisscripting, os, math, tempfile, locale
gp = arcgisscripting.create(9.3)


#directory_name="mezivystupy_hdens"
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
housefld=gp.GetParameterAsText(1)
inlu=gp.GetParameterAsText(2)
lufld=gp.GetParameterAsText(3)
thevalue_l=gp.GetParameterAsText(4)
buffersize=gp.GetParameterAsText(5)

thevalue=thevalue_l.upper()
itsplg="itsplg"

#Check if inputs are corect
#--------------------------
gp.addmessage("Check if inputs are corect")
#0
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in first parametr."
description = gp.describe(inobv)
print description.ShapeType
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#1
#2
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in third parametr."
description = gp.describe(inlu)
print description.ShapeType
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#3
#4

#Calculating id-key in input layer of urban areas
#------------------------------------------------
# gp.addmessage("Calculating id-key in input layer of urban areas")
# gp.addfield(inobv, "idplgfld", "short")
# i=0
# rows = gp.UpdateCursor(inobv)
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

#Summing areas used for living (from polygon landuse layer) in every Urban Area
#------------------------------------------------------------------------------
gp.addmessage("Summing areas used for living (from polygon landuse layer) in every Urban Area")
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

#Calculating density of households in every urban area
#-----------------------------------------------------

polomer_kruhu = int(buffersize)

gp.addmessage("Calculating density of households in every urban area")
gp.addfield(inobv, "hdens", "double")
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    theid=row.Getvalue("idplgfld")
    if theid in listid:
        thenum=row.Getvalue(housefld)
        order=listid.index(theid)
        thearea=listar[order]
        if thearea==0:
            row.setvalue("hdens","0")
            rows.UpdateRow(row)
        elif (thearea/(polomer_kruhu*polomer_kruhu*3.14159265)*100) > 1:
            dens=thenum/thearea
            row.setvalue("hdens", dens)
            rows.UpdateRow(row)
    else:
        row.setvalue("hdens","0")
        rows.UpdateRow(row)
    row = rows.Next()
del row, rows

#Z-score
#-------
gp.addmessage("Z-score")
gp.Statistics_analysis(inobv, "stat.dbf","hdens mean; hdens std")

rows = gp.SearchCursor("stat.dbf") 
row = rows.Next()

themean=row.GetValue("mean_hdens")
thestd=row.GetValue("std_hdens")
print themean, thestd

gp.addfield (inobv, "hdens_z_sc", "double")
rows = gp.UpdateCursor(inobv) 
row = rows.Next()

while row:
    thehdens=row.Getvalue("hdens")
    thehdens_st=(thehdens-themean)/thestd
    row.setvalue("hdens_z_sc", thehdens_st)
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
    thevalue=row.getvalue("hdens_z_sc")
    list_dec.append(thevalue)
    row = rows.Next()
del row, rows

gp.addfield (inobv, "hdens_dec", "double")
list_dec.sort()
print list_dec
thelen=len(list_dec)
p_dec=thelen/float(10)
print p_dec
print thelen, p_dec
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    thevalue=row.getvalue("hdens_z_sc")
    order=list_dec.index(thevalue)
    k=1
    while 1:
        k_dec=k*p_dec
        if order<k_dec:
            row.setvalue("hdens_dec", k)
            rows.UpdateRow(row)
            break
        k=k+1    
    row = rows.Next()
del row, rows 

#gp.deletefield_management(inobv, "idplgfld")
gp.delete_management("stat.dbf")
gp.delete_management(itsplg)
# os.removedirs(directory_name)
gp=None
