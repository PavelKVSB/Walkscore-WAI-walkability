import arcgisscripting, sys, math, os, tempfile, locale
gp = arcgisscripting.create(9.3)


#directory_name="mezivystupy_wai"
#current_folder = os.path.dirname(os.path.realpath(__file__))
#file_folder = os.path.join(current_folder, directory_name)

#if not os.path.exists(file_folder):
#    os.makedirs(os.path.join(current_folder, directory_name))


gp.workspace= 'Data.gdb'
gp.overwriteoutput=1
gp.toolbox = "management", "analysis", "stat"

#Input
#-----
gp.addmessage("Input")
inobv=gp.GetParameterAsText(0)
confld=gp.GetParameterAsText(1)
entfld=gp.GetParameterAsText(2)
farfld=gp.GetParameterAsText(3)
hsdfld=gp.GetParameterAsText(4)

#Check if inputs are corect
#--------------------------
gp.addmessage("Check if inputs are corect")
#0
msg= "This tool was designed to work with Polygon Feature Classes... Please set Polygon feature class in first parametr."
description = gp.describe(inobv)
if description.ShapeType<>"Polygon":
    raise gp.adderror(msg)
#1
#2
#3
#4

#Calculating Walkability index
#-----------------------------
gp.addmessage("Calculating Walkability index")
gp.addfield(inobv, "WAI", "double")
rows = gp.UpdateCursor(inobv)
row = rows.Next()
while row:
    thecon=row.getvalue(confld)
    theent=row.getvalue(entfld)
    thefar=row.getvalue(farfld)
    thehsd=row.getvalue(hsdfld)
    thewai=(2*thecon)+theent+thefar+thehsd
    row.setvalue("WAI",thewai)
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
    thevalue=row.getvalue("WAI")
    list_dec.append(thevalue)
    row = rows.Next()
del row, rows

gp.addfield (inobv, "wai_dec", "double")
list_dec.sort()
print list_dec
thelen=len(list_dec)
p_dec=thelen/float(10)
print p_dec
print thelen, p_dec
rows = gp.UpdateCursor(inobv) 
row = rows.Next()
while row:
    thevalue=row.getvalue("WAI")
    order=list_dec.index(thevalue)
    k=1
    while 1:
        k_dec=k*p_dec
        print k, k_dec
        if order<k_dec:
            print "ano"
            row.setvalue("wai_dec", k)
            rows.UpdateRow(row)
            break
        k=k+1    
    row = rows.Next()
del row, rows
# os.removedirs(directory_name)
gp.workspace=None
gp=None
