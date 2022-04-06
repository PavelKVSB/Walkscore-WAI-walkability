import arcgisscripting, sys, math, os, tempfile

gp = arcgisscripting.create(9.3)

#directory_name="mezivystupy_entropy"
#current_folder = os.path.dirname(os.path.realpath(__file__))
#file_folder = os.path.join(current_folder, directory_name)


#if not os.path.exists(file_folder):
#    os.makedirs(os.path.join(current_folder, directory_name))


gp.workspace= 'Data.gdb'    #file_folder
gp.overwriteoutput=1
gp.toolbox = "management", "analysis", "stat"

#input
#-----
inobv=gp.GetParameterAsText(0)
inlu_w=gp.GetParameterAsText(1)
lufld=gp.GetParameterAsText(2)
val_w=gp.GetParameterAsText(3)

inlu="inlu"
itsplg="intersect"

#check if inputs are corect
#--------------------------
gp.addmessage("Check if inputs are corect")
#0
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in first parametr."
description = gp.describe(inobv)
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#1
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in second parametr."
description = gp.describe(inlu_w)
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#2
#3

#Calculating id-key in input layer of urban areas
#------------------------------------------------
gp.addmessage("Calculating id-key in input layer of urban areas")
gp.addfield_management(inobv, "the_id_obv", "short")
i=0
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    row.setvalue("the_id_obv",i)
    rows.UpdateRow(row)
    i=i+1
    rows.UpdateRow(row) 
    row = rows.Next()
del row, rows

#Erase water bodies from landuse
#-------------------------------
gp.addmessage("Erase water bodies from landuse")
query=str(lufld)+"<>'"+str(val_w)+"'"
gp.select_analysis(inlu_w, inlu, query)

#Intersect input landuse layer and layer of urban areas
#------------------------------------------------------
gp.addmessage("Intersect input landuse and layer of urban areas")
gp.Intersect_analysis([inobv,inlu], itsplg),
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

#Calculating areas of landuse classes in every urban area
#--------------------------------------------------------
gp.addmessage("Calculating areas of landuse classes in every urban area")
gp.Statistics("intersect.shp", "sumstat.dbf", "area sum", "the_id_obv;" + lufld)

rows = gp.SearchCursor("sumstat.dbf") 
row = rows.Next()
sezid=[]
sezar_b=[]
sezca_b=[]

while row:
    theidplg=row.GetValue("the_id_obv")
    plocha = row.GetValue("sum_area")
    thelu=row.GetValue(lufld)
    theln=len(thelu)
    if theidplg not in sezid:
        for char in thelu:
            area_div=plocha/theln
            sezid.append (theidplg)
            sezar_s=[]
            sezar_s.append(plocha)
            sezar_b.append(sezar_s)
            sezca_s=[]
            sezca_s.append(char)
            sezca_b.append(sezca_s)
    else:
        poradi=sezid.index(theidplg)
        area_div=plocha/theln 
        for char in thelu:
            if char not in sezca_b[poradi]:
                sezar_b[poradi].append(area_div)
                sezca_b[poradi].append(char)
            else:
                poradi_s=sezca_b[poradi].index(char)
                (sezar_b[poradi])[poradi_s]=(sezar_b[poradi])[poradi_s]+area_div      
    row = rows.Next()
del row, rows
print sezid
print sezar_b
print sezca_b

#Ascertain numbers and sums in lists
#-----------------------------------
gp.addmessage("Ascertain numbers and sums in lists")
sezsum=[]
sezcount=[]
for x in sezar_b:
    pocet=len(x)
    sezcount.append(pocet)
    suma=0
    for y in x:
        suma=suma+y
    sezsum.append(suma)

print sezsum
print sezcount

#Calculating entropy
#-------------------
gp.addmessage("Calculating entropy")
sezent=[]
i=0
for x in sezar_b:
    if sezcount[i]==1:
        ent=0
        sezent.append(ent)
    else:
        cit=0
        for y in x:
            cit=cit + (y/sezsum[i]*(math.log(y/sezsum[i])))
        ent=(-1)*(cit/math.log(sezcount[i]))
        sezent.append(ent)
    i=i+1
print sezent

#Filling layer of urban areas by entropy index 
#---------------------------------------------
gp.addmessage("Filling layer of urban areas by entropy index")
gp.addfield(inobv, "ent", "double")
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    theid=row.getvalue("the_id_obv")
    theorder=sezid.index(theid)
    print theorder
    thevalue=sezent[theorder]
    row.setvalue("ent", thevalue)
    rows.UpdateRow(row)
    row = rows.Next()
del row, rows
gp.delete_management(inlu)

#Z-score
#-------
gp.addmessage("Z-score")
gp.Statistics_analysis(inobv, "stat.dbf","ent mean; ent std")

rows = gp.SearchCursor("stat.dbf") 
row = rows.Next()

themean=row.GetValue("mean_ent")
thestd=row.GetValue("std_ent")
print themean, thestd

gp.addfield (inobv, "ent_z_sc", "double")
rows = gp.UpdateCursor(inobv) 
row = rows.Next()

while row:
    theent=row.Getvalue("ent")
    theent_st=(theent-themean)/thestd
    row.setvalue("ent_z_sc", theent_st)
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
    thevalue=row.getvalue("ent_z_sc")
    list_dec.append(thevalue)
    row = rows.Next()
del row, rows

gp.addfield (inobv, "ent_dec", "double")
list_dec.sort()
print list_dec
thelen=len(list_dec)
p_dec=thelen/float(10)
print p_dec
print thelen, p_dec
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    thevalue=row.getvalue("ent_z_sc")
    order=list_dec.index(thevalue)
    k=1
    while 1:
        k_dec=k*p_dec
        print k, k_dec
        if order<k_dec:
            row.setvalue("ent_dec", k)
            rows.UpdateRow(row)
            break
        k=k+1    
    row = rows.Next()
del row, rows    
            
#gp.deletefield_management(inobv, "the_id_obv")
gp.delete_management("intersect.shp")
gp.delete_management("stat.dbf")
gp.delete_management("sumstat.dbf")
#os.removedirs(directory_name)

gp=None
