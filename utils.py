import pymysql
import pyproj
import math

# Connect to the database
connection = pymysql.connect(host = 'moment.usc.edu',
                            user = 'cybershk_ro',
                            password = 'CyberShake2007',
                            database = 'CyberShake')


def getUTM(siteName):
    with connection.cursor() as cursor:
        query3 = '''SELECT CS_Site_Lat, CS_Site_Lon FROM CyberShake_Sites
                    WHERE CS_Short_Name = %s
        '''
        cursor.execute(query3, (siteName))
        location = cursor.fetchall()
        lat, lon = location[0][0], location[0][1]
    myProj = pyproj.Proj(proj ='utm', zone = 11, ellps = 'WGS84')
    return myProj(lon, lat)

# Create instance of Site class by doing site0 = Site('USC', getIM or downloadHazardCurves)
class Site:
    def __init__(self, name, valsToInterp, events=None):
        self.name = name
        self.valsToInterp = valsToInterp
        self.x, self.y = getUTM(name)
        self.events = events

    # Define comparison operators
    def within_x_range(self, s0, s1):
        return (s0.x <= self.x <= s1.x) or (s1.x <= self.x <= s0.x)

    def within_y_range(self, s0, s1):
        return (s0.y <= self.y <= s1.y) or (s1.y <= self.y <= s0.y)

    def y_less_than(self, other):
        return self.y < other.y

    def __repr__(self):
        return f'Sitename {self.name}'

# Shared functions between getCurveInfo and interpolateIM.py
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

def linearCheck(sortedL):
    # Determining S0, S3
    if sortedL[0].y_less_than(sortedL[1]):
        # Download hazard curve of site at L[0]
        s0 = sortedL[0]
        s3 = sortedL[1]
    else:
        s0 = sortedL[1]
        s3 = sortedL[0]
    # Determing S1, S2
    if sortedL[2].y_less_than(sortedL[3]):
        s1 = sortedL[2]
        s2 = sortedL[3]
    else:
        s1 = sortedL[3]
        s2 = sortedL[2]
    # Check if sites form square before interpolating: sides and diagonals
    if (not(9900 <= disFormula(s0.x,s0.y,s1.x,s1.y) <= 10100) or not(9900 <= disFormula(s1.x,s1.y,s2.x,s2.y) <= 10100) or 
        not(9900 <= disFormula(s2.x,s2.y,s3.x,s3.y) <= 10100) or not(9900 <= disFormula(s3.x,s3.y,s0.x,s0.y) <= 10100) or
        not((9900*math.sqrt(2)) <= disFormula(s0.x,s0.y,s2.x,s2.y) <= (math.sqrt(2)*10100)) or not((9900*math.sqrt(2)) <= disFormula(s1.x,s1.y,s3.x,s3.y) <= (math.sqrt(2)*10100))):
        print('Entered sites do not form a square')
        exit()
    # Calculate distances with slanted axis
    yPrime = getDistance(s3.x, s3.y, s2.x, s2.y, sortedL[-1].x, sortedL[-1].y) / 10000
    xPrime =  getDistance(s3.x, s3.y, s0.x, s0.y, sortedL[-1].x, sortedL[-1].y) / 10000
    return s0, s1, s2, s3, yPrime, xPrime
