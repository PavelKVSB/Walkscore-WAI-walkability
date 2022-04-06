# -*- coding: utf-8 -*-
# Import needed libraries
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
import geopandas as gpd
import pandana as pdna
from shapely.geometry import Polygon, LineString, Point, box,shape
from shapely.ops import unary_union,split, snap
from shapely.wkt import loads
import networkx as nx
import momepy
import time

from functools import reduce

import warnings
warnings.filterwarnings('ignore')

from amenity_weight_settings import amenity_weights_sesitivity

##########################################

locality = "Ostrava" # options: Ostrava, Hradec

walk_distance = 2414.02

walk_speed = 0.7 # 0.7 for seniors

Beta_coeff = 153 #153 for seniors


##########################################
print("Loading data..")

if locality=="Hradec":   
    road_network = gpd.read_file("./DATA/StreetNetwork/GIS_OSM_HK_2021_JTSK_SPLIT.shp")  
    pedestrian_network = road_network[(road_network.code != 5131) & (road_network.code != 5111) & (road_network.code != 5112)]  
    centriod_grid = gpd.read_file("./DATA/GRID/grid_stred_hk.shp")
    ctverce_grid_ = gpd.read_file("./DATA/GRID/grid_hk.shp")
    ctverce_grid = ctverce_grid_.set_index('ID500M')
    amenities_layer_all = gpd.read_file("./DATA/Amenities/cile_hk_senior.shp")
elif locality=="Ostrava":
    road_network = gpd.read_file("./DATA/StreetNetwork/GIS_OSM_OS_2021_JTSK_SPLIT.shp")  
    pedestrian_network = road_network[(road_network.code != 5131) & (road_network.code != 5111) & (road_network.code != 5112)]  
    centriod_grid = gpd.read_file("./DATA/GRID/grid_stred_ov.shp")
    ctverce_grid_ = gpd.read_file("./DATA/GRID/grid_ov.shp")
    ctverce_grid = ctverce_grid_.set_index('ID500M')
    amenities_layer_all = gpd.read_file("./DATA/Amenities/cile_ov_senior.shp")
else:
    print("Only Hradec and Ostrava city are supported when using the sample data")
    
centriod_grid['x'] = centriod_grid.geometry.x
centriod_grid['y'] = centriod_grid.geometry.y


amenities_layer_all['x'] = amenities_layer_all.geometry.x
amenities_layer_all['y'] = amenities_layer_all.geometry.y
amenities_layer = amenities_layer_all.loc[amenities_layer_all['w_type'] !=  'other']


dd_function = 'Gaussian'

##########################################
print("Pandana graph is being created..")

def create_graph(gdf, precision=3):
    '''Create a networkx given a GeoDataFrame of lines. Every line will
    correspond to two directional graph edges, one forward, one reverse. The
    original line row and direction will be stored in each edge. Every node
    will be where endpoints meet (determined by being very close together) and
    will store a clockwise ordering of incoming edges.
    '''
      
    G = nx.Graph()

    def make_node(coord, precision):
        return tuple(np.round(coord, precision))

    def add_edges(row, G):
        geometry = row.geometry
        coords = list(geometry.coords)
        geom_r = LineString(coords[::-1])
        coords_r = geom_r.coords
        start = make_node(coords[0], precision)
        end = make_node(coords[-1], precision)

        fwd_attr ={}
        for k,v in row.items():
            fwd_attr[k]=v
        fwd_attr['forward']= 1

        fwd_attr['length']=  geometry.length

        fwd_attr['visited']= 0

        G.add_edge(start, end, **fwd_attr)

    gdf.apply(add_edges, axis=1, args=[G])

    return G

G = create_graph(pedestrian_network)

network_components = []
for i, c in enumerate(nx.connected_components(G)):
    network_components.append(len(c))
    
index_max_network_component = np.argmax(network_components)

G_sub = [G.subgraph(c).copy() for c in nx.connected_components(G)]

edges = nx.to_pandas_edgelist(G_sub[index_max_network_component],'from','to')
to = edges['to'].tolist()
fr = edges['from'].tolist()
fr = list(set(fr))
to = list(set(to))
to.extend(fr)
nodes = list(set(to))
nodes = pd.DataFrame(nodes)
nodes.columns=['x', 'y']
nodes['xy'] = nodes.apply(lambda z: (z.x,z.y),axis=1)


nodes['id'] = nodes.index
edges['to_node']=edges['to'].map(nodes.set_index('xy').id)
edges['from_node']=edges['from'].map(nodes.set_index('xy').id)

 
ped_net = pdna.Network(nodes["x"],
                        nodes["y"],
                        edges["from_node"],
                        edges["to_node"],
                        pd.DataFrame([edges['length']]).T,
                        twoway=True)

##########################################

df_walkscore_temp = []

for num, amenity_weights in enumerate(amenity_weights_sesitivity, start=1):

    num_pois_weights = []
    for key in amenity_weights:
        amenity_type_weight = len(amenity_weights[key])
        num_pois_weights.append(amenity_type_weight)
        
    num_pois = max(num_pois_weights) 
    
    amenities = amenities_layer['w_type'].unique()
    distance = walk_distance
    num_categories = len(amenities) 

    bbox_grid = centriod_grid.total_bounds 

    centriod_grid_buffer = centriod_grid.copy()
    centriod_grid_buffer['geometry'] = centriod_grid_buffer.geometry.buffer(walk_distance)
    centriod_grid_buffer['area'] = centriod_grid_buffer.area

    ped_net.init_pois(num_categories=num_categories, max_dist=distance, max_pois=num_pois)

    amenities_layer['w_type'].value_counts()

    x, y = centriod_grid.x, centriod_grid.y
    centriod_grid["node_ids"] = ped_net.get_node_ids(x, y,mapping_distance=walk_distance) 

    x, y = amenities_layer.x, amenities_layer.y 
    amenities_layer["node_ids"] = ped_net.get_node_ids(x, y)

    access_data = []

    for amenity in amenities:
        pois_subset = amenities_layer[amenities_layer['w_type']==amenity]
        print(amenity)

        ped_net.set_pois(category=amenity, x_col=pois_subset['x'], y_col=pois_subset['y'])

        ameniti_ped_access = ped_net.nearest_pois(distance=distance, category=amenity, num_pois=num_pois, max_distance = float("nan"), include_poi_ids=False)

        ameniti_ped_access['amenity_type']=amenity
        
        access_data.append(ameniti_ped_access)
        
    access_data = pd.concat(access_data)   

    columns =  ['d_'+str(i) for i in range(0,num_pois,1)]
    columns.append('amenity_type')

    access_data.columns = columns

    centriod_grid_data = []

    for amenity in amenities:

        access_data_selection = access_data[access_data.amenity_type == amenity]
        centriod_grid_2 = centriod_grid.copy()

        centriod_grid_2['amenity_type']= amenity
        
        for i in range(num_pois):
            centriod_grid_2['d_{}'.format(i)]=centriod_grid_2['node_ids'].map(access_data_selection['d_{}'.format(i)])
        
        centriod_grid_data.append(centriod_grid_2)

    centriod_grid_data = pd.concat(centriod_grid_data)     

    centriod_grid_data_zero_distances = centriod_grid_data.loc[centriod_grid_data['d_0'] == 0]
    grid_join_amenity = centriod_grid_data_zero_distances.join(amenities_layer.set_index('node_ids'), on='node_ids', lsuffix='_grid', rsuffix='_ame')

    grid_df_coord = gpd.GeoDataFrame(grid_join_amenity, geometry=gpd.points_from_xy(grid_join_amenity.x_grid, grid_join_amenity.y_grid))
    amen_df_coord = gpd.GeoDataFrame(grid_join_amenity, geometry=gpd.points_from_xy(grid_join_amenity.x_ame, grid_join_amenity.y_ame))
    grid_join_amenity['distance'] = grid_df_coord.distance(amen_df_coord, align=False)
    grid_join_amenity_ = grid_join_amenity[['ID500M','distance']]


    def convert_zero_to_dist(row,param=''):
        if row[param] == 0:
            output = grid_join_amenity_.loc[grid_join_amenity_.ID500M == row['ID500M'],'distance'].values[0]
        else:
            output = row[param]
        return output

    for i in range(num_pois):
        centriod_grid_data['d_{}'.format(i)]= centriod_grid_data.apply(convert_zero_to_dist, axis=1, param='d_{}'.format(i)) 
        
        
    def convert_to_time(row,param=''):
        output = row[param]/(walk_speed*60)
        return output

    for i in range(num_pois):
        centriod_grid_data['t_{}'.format(i)]= centriod_grid_data.apply(convert_to_time, axis=1, param='d_{}'.format(i))   
      
    def apply_dd(row,param=''):
        if dd_function == 'Gaussian':
            output = np.exp(-1*(row[param]**2)/Beta_coeff)
        return output

    for i in range(num_pois):
        centriod_grid_data['t_{}_dd'.format(i)]= centriod_grid_data.apply(apply_dd, axis=1, param='t_{}'.format(i)) 
        

    def apply_weights(row,weight_index,param=''):
        typ_amenity = row['amenity_type']
        if 0 <= weight_index < len(amenity_weights[typ_amenity]):
            output = row[param]*amenity_weights[typ_amenity][weight_index] 
        else:
            output = row[param]*0
            
        return output

    for i in range(num_pois):
        centriod_grid_data['t_{}_dd_w'.format(i)]= centriod_grid_data.apply(apply_weights, axis=1, weight_index=i, param='t_{}_dd'.format(i)) 

    def apply_multi(row,param=''):
        output = row[param]*6.67
        return output

    for i in range(num_pois):
        centriod_grid_data['t_{}_dd_w_m'.format(i)]= centriod_grid_data.apply(apply_multi, axis=1, param='t_{}_dd_w'.format(i)) 

    column_list_to_sum = []
    for i in range(num_pois): 
        column_list_to_sum.append('t_{}_dd_w_m'.format(i))

    centriod_grid_data["sum_score1"] = centriod_grid_data[column_list_to_sum].sum(axis=1)
    final_score_1 = centriod_grid_data.groupby(['ID500M'], as_index=False)['sum_score1'].sum()

    ###########################

    print("Intersection density calculation...")

    df_nodes_valency = pd.DataFrame (list(G.degree()), columns = ['coordinates','count'])
    df_nodes_valency[['x', 'y']] = pd.DataFrame(df_nodes_valency['coordinates'].tolist(), index=df_nodes_valency.index)
    df_nodes_valency_gdp = gpd.GeoDataFrame(df_nodes_valency, geometry=gpd.points_from_xy(df_nodes_valency.x,df_nodes_valency.y))
    df_nodes_valency_gdp_export = df_nodes_valency_gdp[['count', 'geometry']]

    len(df_nodes_valency_gdp.index)

    df_nodes_valency_gdp_elim = df_nodes_valency_gdp.query('count > 2')
    r=15/2
    df_nodes_valency_gdp_elim_buffer = df_nodes_valency_gdp_elim.buffer(r)
    df_nodes_valency_gdp_elim_buffer_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(df_nodes_valency_gdp_elim_buffer))
    df_nodes_valency_gdp_elim_buffer_gdf_dissolve = df_nodes_valency_gdp_elim_buffer_gdf.dissolve()
    inter_explode= df_nodes_valency_gdp_elim_buffer_gdf_dissolve.explode(index_parts=True)

    inter_explode['area'] = inter_explode.area
    inter_explode_sel = inter_explode[inter_explode['area'] > (math.pi)*(math.pow(r,2))]
    inter_explode_sel['id'] = inter_explode_sel.reset_index().index
    nodes_in_buffer = df_nodes_valency_gdp_elim.overlay(inter_explode_sel, how='intersection')
    nodes_in_buffer_export = nodes_in_buffer[['count', 'geometry','area','id']]
    nodes_out_buffer = df_nodes_valency_gdp_elim.overlay(inter_explode_sel, how='difference')
    nodes_out_buffer_export = nodes_out_buffer[['count', 'geometry']]
    buffer_dissolve_centriod = inter_explode_sel.centroid
    buffer_dissolve_centriod_gdp = gpd.GeoDataFrame(gpd.GeoSeries(buffer_dissolve_centriod))
    buffer_dissolve_centriod_gdp_rename = buffer_dissolve_centriod_gdp.rename(columns ={0:'geometry'})
    buffer_dissolve_centriod_gdp_rename['count'] = 4

    export1 = nodes_out_buffer_export[['count','geometry']]
    export2 = buffer_dissolve_centriod_gdp_rename[['count','geometry']]
    final_street_crossing = pd.concat([export1,export2])
    final_street_crossing_ = final_street_crossing.reset_index()
    final_street_crossing_final = final_street_crossing_[['count','geometry']]
    final_street_crossing_final_ = final_street_crossing_final.set_crs(epsg=5514, inplace=True)

    intersection_density_data = final_street_crossing_final_.overlay(centriod_grid_buffer, how='intersection')

    intersection_density_data_agregate = intersection_density_data.groupby("ID500M").agg(
        valency_count=pd.NamedAgg(column="count", aggfunc="sum"),
        area=pd.NamedAgg(column="area", aggfunc="first"))
    intersection_density_data_agregate['cross_dens'] = intersection_density_data_agregate['valency_count'] / intersection_density_data_agregate['area']
    intersection_density_data_agregate['ID500M'] = intersection_density_data_agregate.index

    final_score_2 = final_score_1.set_index('ID500M').join(intersection_density_data_agregate.set_index('ID500M'))
    final_score_2['cross_dens_mile2'] = final_score_2['cross_dens'] *2590000
    final_score_2['ID500M'] = final_score_2.index

    print("Block length calculation...")
    pedestrian_network_nodes_removed = momepy.remove_false_nodes(pedestrian_network)
    pedestrian_network_nodes_removed['road_length'] = pedestrian_network_nodes_removed.geometry.length

    pedestrian_network_nodes_removed_centroid = gpd.sjoin(pedestrian_network_nodes_removed,centriod_grid_buffer)

    pedestrian_network_nodes_removed_centroid['geom_centroid'] = gpd.GeoSeries.from_xy(pedestrian_network_nodes_removed_centroid.x, pedestrian_network_nodes_removed_centroid.y,crs="EPSG:5514")
    pedestrian_network_nodes_removed_centroid['geom_buffer'] = pedestrian_network_nodes_removed_centroid.geom_centroid.buffer(walk_distance)
    pedestrian_network_nodes_removed_centroid['crosses_buffer'] = pedestrian_network_nodes_removed_centroid['geometry'].crosses(pedestrian_network_nodes_removed_centroid['geom_buffer'])

    pedestrian_network_nodes_removed_centroid_ = pedestrian_network_nodes_removed_centroid[pedestrian_network_nodes_removed_centroid.crosses_buffer == False]

    pedestrian_network_nodes_removed_centroid_agr = pedestrian_network_nodes_removed_centroid_.groupby("ID500M").agg(
        avg_road_length=pd.NamedAgg(column="road_length", aggfunc="mean"))

    pedestrian_network_nodes_removed_centroid_agr['ID500M'] = pedestrian_network_nodes_removed_centroid_agr.index

    final_score_3 = final_score_2.set_index('ID500M').join(pedestrian_network_nodes_removed_centroid_agr.set_index('ID500M'))

    print("Pedestrian friendliness metrics application..")

    def apply_inter_density(row):
        if (row['cross_dens_mile2'] > 200):
            output = row['sum_score1']
        elif (150 < row['cross_dens_mile2'] <= 200):
            output = row['sum_score1'] - (row['sum_score1'] * 0.01)
        elif (120 < row['cross_dens_mile2'] <= 150):
            output = row['sum_score1'] - (row['sum_score1'] * 0.02)
        elif (90 < row['cross_dens_mile2'] <= 120):
            output = row['sum_score1'] - (row['sum_score1'] * 0.03)
        elif (60 < row['cross_dens_mile2'] <= 90):
            output = row['sum_score1'] - (row['sum_score1'] * 0.04)       
        else:
            output = row['sum_score1'] - (row['sum_score1'] * 0.05)

        return output

    final_score_3['sum_score2']= final_score_3.apply(apply_inter_density, axis=1)

    def apply_road_length(row):
        if (row['avg_road_length'] <= 120):
            output = row['sum_score2']
        elif (120 < row['avg_road_length'] <= 150):
            output = row['sum_score2'] - (row['sum_score2'] * 0.01)
        elif (150 < row['avg_road_length'] <= 165):
            output = row['sum_score2'] - (row['sum_score2'] * 0.02)
        elif (165 < row['avg_road_length'] <= 180):
            output = row['sum_score2'] - (row['sum_score2'] * 0.03)
        elif (180 < row['avg_road_length'] <= 195):
            output = row['sum_score2'] - (row['sum_score2'] * 0.04)       
        else:
            output = row['sum_score2'] - (row['sum_score2'] * 0.05)

        return output

    final_score_3['ws_w_{}'.format(num)]= final_score_3.apply(apply_road_length, axis=1) 
    

    final_score_3_sub = final_score_3[['ws_w_{}'.format(num)]]
    df_walkscore_temp.append(final_score_3_sub)
    
    print("Exporting partial results..")
    
    final_score_3.to_csv("./DATA/Walkscore_results/senior_results/sensitivity/Walkscore_{}_senior_sensitivity_{}.csv".format(locality,num)) 

# Export
print("Exporting final results..")
df_walkscore_temp_add = pd.concat(df_walkscore_temp, axis=1, join='inner')
ctverce_grid_final= ctverce_grid.merge(df_walkscore_temp_add,left_index=True, right_index=True) 
ctverce_grid_final.to_file("./DATA/Walkscore_results/senior_results/sensitivity/Walkscore_{}_senior_sensitivity.shp".format(locality)) 