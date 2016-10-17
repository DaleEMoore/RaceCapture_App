#
# Race Capture App
#
# Copyright (C) 2014-2016 Autosport Labs
#
# This file is part of the Race Capture App
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should
# have received a copy of the GNU General Public License along with
# this code. If not, see <http://www.gnu.org/licenses/>.

import math
RADIUS_EARTH_KM = 6371;

class GeoPoint:
    """
    Represents the concept of a Geographic point.
    """
    def __init__(self, **kwargs):
        self.latitude = 0
        self.longitude = 0

    @classmethod
    def fromPoint(cls, latitude, longitude):
        """
        Factory to create a GeoPoint from the specified point
        :param latitude
        :type  latitude float
        :param longitude
        :type longitude float
        :returns the new instance
        :type GeoPoint
        """
        if not latitude or not longitude:
            raise ValueError("Latitude and Longitude must be provided")
        g = GeoPoint()
        g.latitude = latitude
        g.longitude = longitude
        return g

    @classmethod
    def fromPointJson(cls, geoPointJson):
        g = None
        if geoPointJson:
            g = GeoPoint()
            g.latitude = geoPointJson[0]
            g.longitude = geoPointJson[1]
        return g

    def fromJson(self, geoPointJson):
        try:
            self.latitude = geoPointJson[0]
            self.longitude = geoPointJson[1]
        except:
            print('Malformed GeoPoint: ' + str(geoPointJson))

    def toJson(self):
        return [self.latitude, self.longitude]


    def withinCircle(self, point, radiusDeg):
        rSquared = radiusDeg * radiusDeg
        xdelta = point.longitude - self.longitude
        ydelta = point.latitude - self.latitude
        dsquared = (xdelta * xdelta) + (ydelta * ydelta)
        return rSquared >= dsquared


    def metersToDegrees(self, meters, bearingAngle):
        d = meters / 1000.0
        R = RADIUS_EARTH_KM
        brng = math.radians(bearingAngle)

        lat1 = self.latitude
        lon1 = self.longitude

        lat2 = math.degrees((d / R) * math.cos(brng)) + lat1
        lon2 = math.degrees((d / (R * math.sin(math.radians(lat2)))) * math.sin(brng)) + lon1

        distanceDegrees = math.fabs(math.sqrt(math.pow((lat1 - lat2), 2) + math.pow((lon1 - lon2), 2)))
        return distanceDegrees

class Region:
    name = None
    points = None
    def __init__(self, **kwargs):
        self.points = []
        self.name = ''
    def fromJson(self, regionJson):
        self.name = regionJson.get('name', self.name)
        pointsNode = regionJson.get('points')
        if pointsNode:
            for pointNode in pointsNode:
                p = GeoPoint()
                p.fromJson(pointNode)
                self.points.append(p)

    def toJson(self):
        pass

    def withinRegion(self, geoPoint):
        inside = False
        if geoPoint:
            n = len(self.points)
            y = geoPoint.latitude
            x = geoPoint.longitude
            firstPoint = self.points[0]
            p1x = firstPoint.longitude
            p1y = firstPoint.latitude
            for i in range(n + 1):
                pt = self.points[i % n]
                p2x = pt.longitude
                p2y = pt.latitude
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xints:
                                inside = not inside
                p1x, p1y = p2x, p2y
        return inside
