import pymysql
import argparse
import matplotlib.pyplot as plt
import pyproj
import math

parser = argparse.ArgumentParser('Allow user to input site names, ')
parser.add_argument('--sitenames', nargs='+')
# User can specify a particular event ID: source, rup, rupVar to do the interpolation for
# One event = specific source, rup, rupVar, one rupture = specific source, rup, all events = nothing specified
parser.add_argument('--source')
parser.add_argument('--rup')
parser.add_argument('--rupVar')
parser.add_argument('--interpsitename')
args = parser.parse_args()

# Connect to the database
connection = pymysql.connect(host = 'moment.usc.edu',
                            user = 'cybershk_ro',
                            password = 'CyberShake2007',
                            database = 'CyberShake')

def getUTM(sitename):
    #get lat lon of site
    with connection.cursor() as cursor:
        query3 = '''SELECT CS_Site_Lat, CS_Site_Lon FROM CyberShake_Sites
                    WHERE CS_Short_Name = %s
        '''
        cursor.execute(query3, (sitename))
        location = cursor.fetchall()
        lat, lon = location[0][0], location[0][1]
    myProj = pyproj.Proj(proj ='utm', zone = 11, ellps = 'WGS84')
    x, y = myProj(lon, lat)
    return x, y

def getDistance(point1x, point1y, point2x, point2y, SIx, SIy):
    # Used in bilinear interpolation
    # Find where line point1 to point2 and line interpSite intersect
    m1 = (point2y-point1y) / (point2x-point1x)
    b1 = point2y-m1*point2x
    m2 = -(1/m1)
    b2 = SIy-m2*SIx
    xIntersection = (b2-b1)/(m1-m2)
    yIntersection = m2*xIntersection+b2
    d = (SIx-xIntersection)**2 + (SIy-yIntersection)**2
    return d**0.5

# Used when checking if input sites form a square
def disFormula(x0, y0, x1, y1):
    dsquared = (x0-x1)**2 + (y0-y1)**2
    d = dsquared**0.5
    return d

def getIMValues(nameSite):
    with connection.cursor() as cursor:
        # Query changes depending on what part of event ID is entered
        baseQuery = '''
        SELECT P.Source_ID, P.Rupture_ID, P.Rup_Var_ID, P.IM_Value 
        FROM CyberShake_Sites S, CyberShake_Runs R, PeakAmplitudes P, Studies T, IM_Types I
        WHERE S.CS_Short_Name = %s
        AND S.CS_Site_ID = R.Site_ID
        AND R.Study_ID = T.Study_ID
        AND T.Study_Name = 'Study 22.12 LF'
        AND R.Run_ID = P.Run_ID
        AND I.IM_Type_Component = 'RotD50'
        AND I.IM_Type_Value = 2.0
        AND I.IM_Type_ID = P.IM_Type_ID
        '''
        # Want all events for that site
        if args.source == None and args.rup == None and args.rupVar == None:
            cursor.execute(baseQuery, (nameSite))
        # Want all rupture variations for a specific source and rup for that site
        elif args.source != None and args.rup != None and args.rupVar == None:
            query1 = baseQuery + 'AND P.Source_ID = %s AND P.Rupture_ID = %s'
            cursor.execute(query1, (nameSite, args.source, args.rup))
        # Want one event only
        elif args.source != None and args.rup != None and args.rupVar != None:
            query2 = baseQuery + 'AND P.Source_ID = %s AND P.Rupture_ID = %s And P.Rup_Var_ID = %s'
            cursor.execute(query2, (nameSite, args.source, args.rup, args.rupVar))
        else:
            print('Please enter one event = specific source, rup, rupVar, one rupture = specific source, rup, or all events = nothing specified')
            exit()
        result = cursor.fetchall()
        # Result row = (sourceID, ruptureID, RupVarID, IMVal)
        # EventID = tuple of first three values from result row
        eventID = []
        IMVals = []
        for row in result:
            eventID.append((row[0], row[1], row[2]))
            IMVals.append(row[3])
        return eventID, IMVals

def bilinearinterpolation(s0, s1, s2, s3, sI):
    p0x, p0y = getUTM(s0)
    p1x, p1y = getUTM(s1)
    p2x, p2y = getUTM(s2)
    p3x, p3y = getUTM(s3)
    x, y = getUTM(sI)
    # Store event ID from smallest input site
    eventIDs = getIMValues(s0)[0], getIMValues(s1)[0], getIMValues(s2)[0], getIMValues(s3)[0], getIMValues(sI)[0]
    minEventIDs = min(eventIDs,key=len)
    interpolatedIMVals = []
    # List to store shared events between the sites
    interpEvents = []
    # xCoords = event IDs, yCoords = IM Vals
    listPXY = [(p0x, p0y, getIMValues(s0)[1]), (p1x, p1y, getIMValues(s1)[1]), (p2x, p2y, getIMValues(s2)[1]), (p3x, p3y, getIMValues(s3)[1])]
    sortedL = sorted(listPXY, key=lambda x:x[0])
    # Determining S0, S3
    if sortedL[0][1] < sortedL[1][1]:
        (x0, y0, IMVals0) = sortedL[0]
        (x3, y3, IMVals3) = sortedL[1]
    else:
        (x0, y0, IMVals0) = sortedL[1]
        (x3, y3, IMVals3) = sortedL[0]
    # Determing S1, S2
    if sortedL[2][1] < sortedL[3][1]:
        (x1, y1, IMVals1) = sortedL[2]
        (x2, y2, IMVals2) = sortedL[3]
    else:
        (x1, y1, IMVals1) = sortedL[3]
        (x2, y2, IMVals2) = sortedL[2]
    # Check if sites form square before interpolating: sides and diagonals
    if (not(9900 <= disFormula(x0,y0,x1,y1) <= 10100) or not(9900 <= disFormula(x1,y1,x2,y2) <= 10100) or 
        not(9900 <= disFormula(x2,y2,x3,y3) <= 10100) or not(9900 <= disFormula(x3,y3,x0,y0) <= 10100) or
        not((9900*math.sqrt(2)) <= disFormula(x0,y0,x2,y2) <= (math.sqrt(2)*10100)) or not((9900*math.sqrt(2)) <= disFormula(x1,y1,x3,y3) <= (math.sqrt(2)*10100))):
        print('Entered sites do not form a square')
        exit()
    # Calculate distances with slanted axis
    yPrime = getDistance(x3, y3, x2, y2, x, y) / 10000
    xPrime =  getDistance(x3, y3, x0, y0, x, y) / 10000
    for i in range(len(minEventIDs)):
        continueOuterLoop = False
        eventID = minEventIDs[i]
        for list in eventIDs:
            # Event IDs might have different indexes in list of IDs for site
            if eventID not in list:
                continueOuterLoop = True
        if continueOuterLoop:
            continue
        R1 = (IMVals0[i] * (1-xPrime) + IMVals1[i] * xPrime)
        R2 = (IMVals2[i] * xPrime + IMVals3[i] * (1-xPrime))
        interpVal = (R1 * yPrime + R2 * (1-yPrime))
        interpolatedIMVals.append(interpVal)
        interpEvents.append(eventID)
    # TEMPORARY -> print out interpolated and event values
    print('\nInterp values')
    for val in interpolatedIMVals:
        print(val)
    print('\nEventID values')
    for v in interpEvents:
        print(v)

def interpScatterplot():
    # Make scatterplot of actual IM values versus interpolated
    # Have y = x as reference
    pass

def main():
    sites = (args.sitenames[0]).split(',')
    site0, site1, site2, site3 = sites[0], sites[1], sites[2], sites[3]
    # Just bilin interpolation for now, can add 1d linear later
    bilinearinterpolation(site0, site1, site2, site3, args.interpsitename)
    connection.close()

main()