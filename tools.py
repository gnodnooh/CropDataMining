import os
import numpy as np
import pandas as pd
import geopandas as gpd
import math
import shapefile as shp
import fiona
from shapely.geometry import shape, mapping
import rtree
import matplotlib.pyplot as plt
import matplotlib.colors as colors


def IntersectShapefiles(refSHP, admSHP, outSHP, set_print=True):

    # Source: https://gis.stackexchange.com/a/119397
    # Revised by Donghoon Lee 09-27-2020
    
    with fiona.open(refSHP, 'r') as layer1:
        with fiona.open(admSHP, 'r') as layer2:
            # We copy schema and add the  new property for the new resulting shp
            schema = layer2.schema.copy()
            schema['properties']['ID'] = 'int:10'
            # We open a first empty shp to write new content from both others shp
            with fiona.open(outSHP, 'w', 'ESRI Shapefile', schema) as layer3:
                index = rtree.index.Index()
                for feat1 in layer1:
                    fid = int(feat1['id'])
                    geom1 = shape(feat1['geometry'])
                    index.insert(fid, geom1.bounds)

                for feat2 in layer2:
                    geom2 = shape(feat2['geometry'])
                    for fid in list(index.intersection(geom2.bounds)):
                        if fid != int(feat2['id']):
                            feat1 = layer1[fid]
                            geom1 = shape(feat1['geometry'])
                            if geom1.intersects(geom2):
                                # We take attributes from admSHP
                                props = feat2['properties']
                                # Then append the uid attribute we want from the other shp
                                props['ID'] = feat1['properties']['ID']
                                # Add the content to the right schema in the new shp
                                layer3.write({
                                    'properties': props,
                                    'geometry': mapping(geom1.intersection(geom2))
                                })

    # Save a projection file (filename.prj)
    filename, _ = os.path.splitext(outSHP)
    prj = open("%s.prj" % filename, "w") 
    epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]' 
    prj.write(epsg)
    prj.close()
    if set_print:
        print('%s is saved.' % outSHP)

    
    
def CreateGridBox_subextent(shp_out, extent, dx, dy, sub_extent, set_print=True):
    '''Create grid with degrees of extent, dx, dy of the target box
    
    Parameters
    ----------
    extent: list
        [minx,maxx,miny,maxy]
    dx: value
        degree of x
    dy: value
        degree of y

    Returns
    -------
    shp_out file is created.
    
    
    Source: https://gis.stackexchange.com/a/81120/29546
    Revised by Donghoon Lee @ Sep-24-2020
    '''
    
    # Size of extent
    width = np.round((extent[1] - extent[0])/dx)
    height = np.round((extent[3] - extent[2])/dy)
    
    # Adjust sub_extent with base grid extent
    minx = extent[0] + np.floor((sub_extent[0] - extent[0])/dx)*dx
    maxx = extent[0] + np.ceil((sub_extent[1] - extent[0])/dx)*dx
    maxy = extent[3] - np.floor((extent[3] - sub_extent[3])/dy)*dy
    miny = extent[3] - np.ceil((extent[3] - sub_extent[2])/dy)*dy
    sub_extent = [minx, maxx, miny, maxy]
    
    # Index of sub_extent
    left = np.floor((sub_extent[0] - extent[0])/dx)
    right = np.floor((sub_extent[1] - extent[0])/dx)
    top = np.floor((extent[3] - sub_extent[3])/dy)
    bottom = np.floor((extent[3] - sub_extent[2])/dy)
    
    # # Create vertices per each grid
    nx = int(math.ceil(abs(maxx - minx)/dx))
    ny = int(math.ceil(abs(maxy - miny)/dy))
    w = shp.Writer(shp_out, shp.POLYGON)
    w.autoBalance = 1
    w.field("ID")
    id=int(top*width+left)  # Initial ID
    for i in range(ny):
        for j in range(nx):
            vertices = []
            parts = []
            vertices.append([min(minx+dx*j,maxx),max(maxy-dy*i,miny)])
            vertices.append([min(minx+dx*(j+1),maxx),max(maxy-dy*i,miny)])
            vertices.append([min(minx+dx*(j+1),maxx),max(maxy-dy*(i+1),miny)])
            vertices.append([min(minx+dx*j,maxx),max(maxy-dy*(i+1),miny)])
            parts.append(vertices)
            w.poly(parts)
            w.record(id)
            id+=1
        id+=int(width-nx)
    w.close()
    
    
    # Save a projection file (filename.prj)
    filename, _ = os.path.splitext(shp_out)
    prj = open("%s.prj" % filename, "w")
    epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]' 
    prj.write(epsg)
    prj.close()
    if set_print:
        print('%s is saved.' % shp_out)

        
def CreateGridBox(shp_out, extent, dx, dy, set_print=True):
    '''Create grid with degrees of extent, dx, dy of the target box
    
    Parameters
    ----------
    extent: list
        [minx,maxx,miny,maxy]
    dx: value
        degree of x
    dy: value
        degree of y

    Returns
    -------
    shp_out file is created.
    
    
    Source: https://gis.stackexchange.com/a/81120/29546
    Revised by Donghoon Lee @ Aug-10-2019
    '''
    minx,maxx,miny,maxy = extent
    nx = int(math.ceil(abs(maxx - minx)/dx))
    ny = int(math.ceil(abs(maxy - miny)/dy))
    w = shp.Writer(shp_out, shp.POLYGON)
    w.autoBalance = 1
    w.field("ID")
    id=0
    for i in range(ny):
        for j in range(nx):
            vertices = []
            parts = []
            vertices.append([min(minx+dx*j,maxx),max(maxy-dy*i,miny)])
            vertices.append([min(minx+dx*(j+1),maxx),max(maxy-dy*i,miny)])
            vertices.append([min(minx+dx*(j+1),maxx),max(maxy-dy*(i+1),miny)])
            vertices.append([min(minx+dx*j,maxx),max(maxy-dy*(i+1),miny)])
            parts.append(vertices)
            w.poly(parts)
            w.record(id)
            id+=1
    w.close()
    
    # Save a projection file (filename.prj)
    filename, _ = os.path.splitext(shp_out)
    prj = open("%s.prj" % filename, "w")
    epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]' 
    prj.write(epsg)
    prj.close()
    if set_print:
        print('%s is saved.' % shp_out)

    
def save_hdf(filn, df, set_print=True):
    df.to_hdf(filn, key='df', complib='blosc:zstd', complevel=9)
    if set_print:
        print('%s is saved.' % filn)
        
        
# Colarmap and Colorbar controller
def cbarpam(bounds, color, labloc='on', boundaries=None, extension=None):
    '''Returns parameters for colormap and colorbar objects with a specified style.

        Parameters
        ----------
        bounds: list of bounds
        color: name of colormap or list of color names

        labloc: 'on' or 'in'
        boundaries: 
        extension: 'both', 'min', 'max'

        Return
        ------
        cmap: colormap
        norm: nomalization
        vmin: vmin for plotting
        vmax: vmax for plotting
        boundaries: boundaries for plotting
        
        Donghoon Lee @ Mar-15-2020
    '''
    
    gradient = np.linspace(0, 1, len(bounds)+1)
    # Create colorlist
    if type(color) is list:
        cmap = colors.ListedColormap(color,"")
    elif type(color) is str:
        cmap = plt.get_cmap(color, len(gradient))    
        # Extension
        colorsList = list(cmap(np.arange(len(gradient))))
        if extension is 'both':
            cmap = colors.ListedColormap(colorsList[1:-1],"")
            cmap.set_under(colorsList[0])
            cmap.set_over(colorsList[-1])
        elif extension is 'max':
            cmap = colors.ListedColormap(colorsList[:-1],"")
            cmap.set_over(colorsList[-1])
        elif extension is 'min':
            cmap = colors.ListedColormap(colorsList[1:],"")
            cmap.set_under(colorsList[0])
        elif extension is None:
            gradient = np.linspace(0, 1, len(bounds)-1)
            cmap = plt.get_cmap(color, len(gradient))
        else:
            raise ValueError('Check the extension')
    else:
        raise ValueError('Check the type of color.')
    # Normalization
    norm = colors.BoundaryNorm(bounds, cmap.N)
    # vmin and vmax
    vmin=bounds[0]
    vmax=bounds[-1]
    # Ticks
    if labloc == 'on':
        ticks = bounds
    elif labloc == 'in':
        ticks = np.array(bounds)[0:-1] + (np.array(bounds)[1:] - np.array(bounds)[0:-1])/2
    
    return cmap, norm, vmin, vmax, ticks, boundaries
