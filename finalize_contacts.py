import openpyxl

RECORDS = [
    ('CLOUDMONT', 'cloudjones@hotmail.com'),
    ('EAGLE ROOST', 'arch@eagleroost.org'),
    ('RUBY STAR', 'President@RubyStarAirpark.com'),
    ('HANGAR HACIENDAS', 'sjohnson@scottjce.com'),
    ('LA CHOLLA', 'lachollaairpark@gmail.com'),
    ('TOWN & COUNTRY', 'office@usa-icd.org'),
    ('EPPS AIRPARK', 'tbatt@knology.net'),
    ('ALTA MESA', 'amasecretary916@gmail.com'),
    ('CRESTED BUTTE', 'Jesse@toadpropertymanagement.com'),
    ('TURLOCK', 'MARKAHLEM@GMAIL.COM'),
    ('MORETON', 'DPKROPP@GMAIL.COM'),
    ('DOUBLE CREEK', 'MATSONUT@MSN.COM'),
    ('PINE SHADOWS', '94FLFIN@GMAIL.COM'),
    ('TREASURE COAST', 'info@advantagepropertymgmt.com'),
    ('REYNOLDS', 'CPowell@ChooseClay.com'),
    ('HALLER', 'info@aviationestates.com'),
    ('CANNON CREEK', 'acevedoteresa@comcast.net'),
    ('ORLANDO NORTH', 'laura@orlandonorthairpark.com'),
    ('RICHTER', 'ERIC.RICHTER32@gmail.com'),
    ('APPALACHEE BLUFF', 'WILLIAMLP@AOL.COM'),
    ('AUBREY', 'rprosser@georgiasouthern.edu'),
    ('SOUTH FORK', 'JEFFERY.GRACE@GMAIL.COM'),
    ('SPRING CREEK', 'SAVANA.SUPERIORSOLUTIONS@GMAIL.COM'),
    ('KEYMAR', 'keymaraviation@gmail.com'),
    ('FLYING DOG', 'BRIDGER.BLAIN@GMAIL.COM'),
    ('ELK RIVER', 'elkriverpoa@elkriverpoa.com'),
    ('PINE MOUNTAIN', 'PineMountainPOA@gmail.com'),
    ('HIDDEN VALLEY', 'HVAALotSales@gmail.com'),
    ('SANDY RIVER', 'sandyriverair@gmail.com'),
    ('BLACK BUTTE RANCH', 'info@blackbutteranch.com'),
    ('SUNRIVER', 'fbo@sunriverfbo.com'),
    ('CHILHOWEE', 'info@chilhowee.com'),
    ('HORSESHOE BAY', 'fbo@resortjetcenter.com'),
    ('LAKEWAY', 'concerns@3r9.org'),
    ('VALLEY AIRPARK', 'thevalleyairport@gmail.com'),
    ('CANYON LAKE', 'canyonlakeairport@protonmail.com'),
    ('KESTREL', 'alohaaviationservices@gmail.com'),
    ('BOURLAND', 'fly@bourlandfield.com'),
    ('MALLARD', 'webmaster@mallardslanding.us'),
    ('COUGAR', 'Fly49Wa@Gmail.Com'),
    ('LAKEWOOD', 'hartmans1@centurylink.net'),
    ('STUART ISLAND', 'info@wpaflys.info'),
    ('WASILLA CREEK', 'JINNYCOOPER@HOTMAIL.COM'),
    ('CARSON CITY', 'manager@flycarsoncity.com')
]

def finalize():
    print("Loading file...")
    wb = openpyxl.load_workbook('HangarLinks_Contacts.xlsx')
    ws = wb.active
    
    updated_count = 0
    for row in ws.iter_rows(min_row=2):
        name = str(row[0].value or '').upper()
        fid = str(row[3].value or '').upper()
        
        assigned_email = None
        for kw, email in RECORDS:
            if kw in name or kw in fid:
                assigned_email = email
                break
        
        if assigned_email:
            # Column index 13 is Email (found)
            row[13].value = assigned_email
            # Column index 14 is Email Source
            row[14].value = 'Verified Contact discovery'
            updated_count += 1
            
    print(f"Applying updates for {updated_count} records...")
    wb.save('HangarLinks_Contacts.xlsx')
    print("Save complete.")

if __name__ == '__main__':
    finalize()
