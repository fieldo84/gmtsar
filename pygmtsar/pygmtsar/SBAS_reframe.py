# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2021, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .SBAS_reframe_gmtsar import SBAS_reframe_gmtsar
from .S1 import S1
from .PRM import PRM

class SBAS_reframe(SBAS_reframe_gmtsar):

    def get_pins(self, subswath=None):
        print ('The function is obsolete, and it does nothing. Use SBAS.reframe_parallel(geometry=...) to crop bursts.')
        return []

    def set_pins(self, *args):
        print ('The function is obsolete, and it does nothing. Use SBAS.reframe_parallel(geometry=...) to crop bursts.')
        return
    
    def reframe(self, subswath, date, geometry=None, debug=False):
        """
        Estimate framed area using Sentinel-1 GCPs approximation.

        Parameters
        ----------
        subswath : int
            The subswath number.
        date : str
            The date of the scene.
        geometry: shapely.geometry of geopandas.GeoSeries or geopandas.GeoDataFrame
            Optional geometry covering required bursts to crop the area.
        debug : bool, optional
            Enable debug mode. Default is False.

        Returns
        -------
        pandas.DataFrame
            The updated DataFrame with the estimated framed area.

        Examples
        --------
        df = sbas.reframe(1, '2023-05-20')
        """
        import geopandas as gpd
        import numpy as np
        #import shapely
        from shapely.geometry import Point, LineString, Polygon, MultiPolygon
        from datetime import datetime
        import os

        # define line covering some bursts to crop them
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry = geometry.unary_union
        # convert to polygon when possible
        geometry = geometry.minimum_rotated_rectangle
        # it can be point or line or polygon
        if isinstance(geometry, Point):
            # create ~100m buffer around
            #geometry = geometry.buffer(1e-3)
            raise ValueError(f"Unsupported Point geometry. Unfortunately, GMTSAR tools cannot crop a scene to a single burst.")
        if isinstance(geometry, Polygon):
            rect = geometry.minimum_rotated_rectangle.exterior
            # define diagonal line
            diag1 = LineString([rect.coords[0], rect.coords[2]])
            diag2 = LineString([rect.coords[1], rect.coords[3]])
            if diag1.length <= diag2.length:
                geometry = diag1
            else:
                geometry = diag2
        if debug:
            print ('DEBUG: geometry', geometry)
    
        df = self.get_repeat(subswath, date)
        stem = self.multistem_stem(subswath, df['datetime'][0])[1]
        #print ('stem', stem)

        old_filename = os.path.join(self.basedir, f'{stem}')
        #print ('old_filename', old_filename)

        self.make_s1a_tops(subswath, date, debug=debug)

        prm = PRM.from_file(old_filename+'.PRM')
        tmpazi_a = prm.SAT_llt2rat([geometry.coords[0][0],  geometry.coords[0][1],  0], precise=1, debug=debug)[1]
        tmpazi_b = prm.SAT_llt2rat([geometry.coords[-1][0], geometry.coords[-1][1], 0], precise=1, debug=debug)[1]
        tmpazi = min(tmpazi_a, tmpazi_b)
        if debug:
            print ('DEBUG: ','tmpazi', tmpazi)
        prm.shift_atime(tmpazi, inplace=True).update()
        azi_a = prm.SAT_llt2rat([geometry.coords[0][0], geometry.coords[0][1], 0], precise=1, debug=debug)[1] + tmpazi
        azi_b = prm.SAT_llt2rat([geometry.coords[-1][0], geometry.coords[-1][1], 0], precise=1, debug=debug)[1] + tmpazi
        # reorder boundaries for orbit
        azi1 = min(azi_a, azi_b)
        azi2 = max(azi_a, azi_b)
        if debug:
                print ('DEBUG: ','azi1', azi1, 'azi2', azi2)

        # Working on bursts covering $azi1 ($ll1) - $azi2 ($ll2)...
        #print ('assemble_tops', subswath, date, azi1, azi2, debug)
        self.assemble_tops(subswath, date, azi1, azi2, debug=debug)

        # Parse new .xml to define new scene name
        # like to 's1b-iw3-slc-vv-20171117t145922-20171117t145944-008323-00ebab-006'
        filename = os.path.splitext(os.path.split(df['datapath'][0])[-1])[0]
        head1 = filename[:15]
        tail1 = filename[-17:]
        xml_header = S1.read_annotation(old_filename+'.xml')['product']['adsHeader']
        date_new = xml_header['startTime'][:10].replace('-','')
        t1 = xml_header['startTime'][11:19].replace(':','')
        t2 = xml_header['stopTime'][11:19].replace(':','')
        new_name = f'{head1}{date_new}t{t1}-{date_new}t{t2}-{tail1}'
        new_filename = os.path.join(self.basedir, new_name)
        #print ('new_filename', new_filename)

        # rename xml and tiff
        for ext in ['.tiff', '.xml']:
            if debug:
                print('DEBUG: rename', old_filename+ext, new_filename+ext)
            os.rename(old_filename+ext, new_filename+ext)

        # cleanup
        for fname in [old_filename+'.LED', old_filename+'.PRM']:
            if not os.path.exists(fname):
                continue
            if debug:
                print ('DEBUG: remove', fname)
            os.remove(fname)

        # update and return only one record
        df = df.head(1)
        #df['datetime'] = self.text2date(f'{date_new}t{t1}', False)
        df['datetime'] = datetime.strptime(f'{date_new}T{t1}', '%Y%m%dT%H%M%S')
        df['metapath'] = new_filename + '.xml'
        df['datapath'] = new_filename + '.tiff'
        # update approximate location
        df['geometry'] = MultiPolygon([geom for geom in df['geometry'][0].geoms if geom.intersects(geometry)])

        return df

    def reframe_parallel(self, geometry=None, n_jobs=-1, **kwargs):
        """
        Reorder bursts from sequential scenes to cover the full orbit area or some bursts only.

        Parameters
        ----------
        geometry: shapely.geometry of geopandas.GeoSeries or geopandas.GeoDataFrame
            Optional geometry covering required bursts to crop the area.
        n_jobs : int, optional
            Number of parallel processing jobs. n_jobs=-1 means all the processor cores are used.

        Returns
        -------
        None

        Examples
        --------
        Without defined geometry the command is silently skipped:
        sbas.reframe_parallel()
        
        Define a line partially covering two bursts:
        sbas.reframe_parallel(geometry=LineString([Point(25.3, 35.0), Point(25, 35.2)]))
        
        Read the geometry from GeoJSON file and convert to WGS84 coordinates:
        AOI = gpd.GeoDataFrame().from_file('AOI.json').to_crs(4326)
        sbas.reframe_parallel(geometry=AOI)
        
        TODO: Define a point on a selected burst (this option is not available now):
        sbas.reframe_parallel(geometry=Point(25.3, 35))
        """
        from tqdm.auto import tqdm
        import joblib
        import pandas as pd

        if geometry is None:
            print ('Reframing is skipped because the geometry argument is not defined.')
            return

        dates = self.df.index.unique().values

        subswaths = self.get_subswaths()

        # process all the scenes
        with self.tqdm_joblib(tqdm(desc='Reframing', total=len(dates)*len(subswaths))) as progress_bar:
            records = joblib.Parallel(n_jobs=n_jobs)(joblib.delayed(self.reframe)(subswath, date, geometry, **kwargs) \
                                                     for date in dates for subswath in subswaths)

        self.df = pd.concat(records)
