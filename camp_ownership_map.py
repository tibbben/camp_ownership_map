# -*- coding: utf-8 -*-

"""
Module Name: camp_ownership_map.py
Description: Filters the ownership columns in the Miami-Dade County parcels and assigns
             a standard set of categories for the Climate Equity & Mapping Platform
             (CAMP) created by the Univeristy of Miami Office of Civic and Community 
             Engagement (CCE). There are three main steps in the pipeline:
             
             1. predefined ownership cagtegories are assigned to the parcels (see csv/ownership_map.cs)
             2. an exclusion filter is run to remove certain types of owners (see csv/exclusion.csv)
             3. underutilization catgories are assigend based on predefined criteria. See:
                https://miami.app.box.com/integrations/officeonline/openOfficeOnline?fileId=1676462145432
      
The results are seved to:
    base_path/data/mdc_parcels_camp_ownership/download/mdc_parcels_camp_ownership.json

Usage:
    python camp_ownership_map.py /path/to/mdc_parcels_camp_filtered.json

Dependencies:
    - pandas >= 2.0
"""

# Metadata
__author__ = "Tim Norris"
__copyright__ = "Copyright 2026, University of Miami CCE and University of Miami IDSC"
__credits__ = ["Chelsea Lafrance"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Tim Norris"
__email__ = "tnorris@miami.edu"
__status__ = "Production"

import pandas as pd
import sys
import json

# could br read from metadata ...
camp_columns = [
    "mdc_county_zone",
    "mdc_county_zone_desc",
    "mdc_municipal_zone",
    "mdc_municipal_zone_desc",
    "fema_flood_zone",
    "mdc_qualified_opportunity_zones",
    "mdc_neighborhood_name",
    "mdc_municipal_boundary_name",
    "com_neighborhood_name",
    "cce_land_use",
    "elevation",
    "exclude",
    "include",
    "mdc_road_id",
    "mdc_road_type",
    "mdc_street_id",
    "mdc_street_type",
    "mdc_municipal_park_folio",
    "mdc_county_park_folio",
    "fmla_area_type",
    "mdc_urban_growth_boundary",
    "mdc_building_density",
    "camp_ownership",
    "camp_categories",
    "underutilized",
    "spatial",
    "regulatory",
    "shape_area",
    "shape_length"
]
        
def create_condition(owner: str, parcels: pd.DataFrame) -> pd.Series:
    """
    py:function:: create_condition(owner, parcels)
    
    Create a conditional array to filter the parcels dataframe for an ownership
    category using a formatted string from the OwnsershipMap file.

    :param str owner: a stricly formatted string that defines a filter combination
    :param parcels pd.DataFrame: the parcels dataframe
    :return: a boolean series for the parcels built from the string
    :rtype: pd.Series
    """
    
    owner = owner.split('&&')
    
    if '!' not in owner[0]: # simple CONTAIN conditional on true_owner1
        lb = parcels['true_owner1'].str.contains(owner[0])
        
    else: # AND NOT CONTAIN conditionals on true_owner1
        owner1s = owner[0].split('!')
        lb = parcels['true_owner1'].str.contains(owner1s[0])
        for owner1 in owner1s[1:]:
            lb = lb & ~parcels['true_owner1'].str.contains(owner1,na=False)
        lb = (lb)       
    
    if len(owner) > 1:    
        for owner2 in owner[1:]: # AND [NOT] CONTAIN conditionals on true_owner2
            if '!' not in owner2:
                lb = lb & parcels['true_owner2'].str.contains(owner2)
            else:
                owner2s = owner2.split('!')
                if len(owner2s[0]) > 0:
                    lb = lb & parcels['true_owner2'].str.contains(owner2s[0],na=False)
                for owner2 in owner2s[1:]:
                    lb = lb & ~parcels['true_owner2'].str.contains(owner2,na=False)
        lb = (lb)
            
    #return lb.infer_objects(copy=False)
    return lb.astype(bool).fillna(False)

def assign_ownership(parcels: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    """
    py:function:: assign_ownership(parcels, categories)
    
    Assign ownership from the predefined categories to parcels.

    :param parcels pd.DataFrame: the parcels dataframe
    :param categories pd.DataFrame: the ownership map categories dataframe
    :return: the updated parcels dataframe
    :rtype: pd.DataFrame
    """
    
    def filter_and_assign(category: pd.Series, parcels: pd.DataFrame) -> str:
        """
        py:function:: filter_and_assign(category, parcels)
    
        Filter on one ownership and assign the ownership category.
        """
        
        true_owner = category['true_owner[123]'].split('|')
        # print(category['Ownership'])

        # create the conditional pandas array to filter rows in the parcels
        b = create_condition(true_owner[0], parcels)
        for sub_owner in true_owner[1:]:
            b = b | create_condition(sub_owner, parcels)

        # set the ownership and categories in the parcels with the conditional array
        parcels.loc[b,'camp_ownership'] = category['Ownership']
        parcels.loc[b,'camp_categories'] = category['Owner Categories']

        return category['Ownership']
    
    # add columns for new categories
    parcels['camp_ownership'] = ''
    parcels['camp_categories'] = ''
    
    return categories.apply(filter_and_assign, parcels=parcels, axis=1)

def exclude(parcels: pd.DataFrame, exclusion: pd.DataFrame) -> None:
    """
    py:function:: exclude(parcels,exclusion)
    
    Add exclusion filters to exclude column in parcels

    :param parcels pd.DataFrame: the parcels dataframe
    :param exclusion pd.DataFrame: the set of conditions for exclusion
    :return: the parcels dataframe is updated in place
    :rtype: None
    """
    
    def filter_and_assign(exclude: pd.Series, parcels: pd.DataFrame) -> None:
        """
        py:function:: filter_and_assign(exclude, parcels)
        
        filter on one exclusion and assign value to exclude
        """
        
        # print(exclude['Exclusion'])
        b = (parcels['true_owner1'].str.contains(exclude['Exclusion'],case=False) | \
             parcels['true_owner2'].str.contains(exclude['Exclusion'],case=False) | \
             parcels['true_owner3'].str.contains(exclude['Exclusion'],case=False) )
        if not exclude['Global']: b = b & (parcels['camp_ownership'] == '')
        b = b.astype(bool).fillna(False)

        # directly update the parcels df
        parcels.loc[b,'exclude'] = f"|{exclude['Exclusion']}|" 
        
    if 'exclude' not in parcels: parcels['exclude'] = ''
    exclusion.apply(filter_and_assign, parcels=parcels, axis=1)

def main():
    """
    py:function:: main()
    
    Read the parcel and categegory files and process. There are three main steps in
    the pipeline:
      1. predefined ownership cagtegories are assigned to the parcels (see csv/ownership_map.cs)
      2. an exclusion filter is run to remove certain types of owners (see csv/exclusion.csv)
      3. underutilization catgories are assigend based on predefined criteria. See:
         https://miami.app.box.com/integrations/officeonline/openOfficeOnline?fileId=1676462145432
      
    The results are seaved to:
      base_path/data/mdc_parcels_camp_ownership/download/mdc_parcels_camp_ownership.json

    :return: the updated parcels are saved to a file
    :rtype: None
    """

    if len(sys.argv) == 2:
        parcel_file = sys.argv[1]
    else: # default for testing
        base_path = "D:/Sync/gitRepos/projects/gdsc/_localdata"
        #base_path = "/Users/tibben/Documents/Sync/UMCCS/gdsc/_localdata"
        parcel_file = f"{base_path}/data/mdc_parcels_camp_filtered/derived/mdc_parcels_camp_filtered.json"

    # load test parcel data and category map
    path = ("/").join(parcel_file.split("/")[:-1])
    if path == "": path = "./" 
    file = parcel_file.split("/")[-1].split(".")[0]
    ext = parcel_file.split("/")[-1].split(".")[1]
    print(path,file,ext)
    if "json" in ext:
        with open(parcel_file, 'r') as f:
            data = json.load(f)
        parcels = pd.json_normalize(data['features'])
        rename = {}
        for col in list(parcels):
            if 'properties' in col: rename[col] = col.lower()[11:]
        parcels = parcels.rename(columns=rename)
    elif ext == "csv":
        parcels = pd.read_csv(parcel_file, low_memory=False)
    categories = pd.read_csv('csv/ownership_map.csv')

    # assign ownership according to the ownershipmap.csv
    owner_filters = assign_ownership(parcels,categories)
    
    # catch all remaining religious organizations
    b = parcels['dor_desc'].str.contains("RELIGIOUS.*",na=False)
    parcels.loc[b,'camp_ownership'] = "Religious"
    parcels.loc[b,'camp_categories'] = "Institutional"

    # give feedback
    #for owner_filter in owner_filters:
    #    print((
    #        f"{owner_filter} "
    #        f"original {len(parcels[parcels['Ownership'].str.strip()==owner_filter])} "
    #        f"test {len(parcels[parcels['camp_ownership'].str.strip()==owner_filter])}"
    #    ))
        
    # add final exclude conditions to exclude field
    exclusion = pd.read_csv('csv/exclusion.csv')
    exclude(parcels,exclusion)
    
    # filter out unwanted parcels
    parcels = parcels[
        (
            (parcels['exclude'].isna()) | 
            (parcels['exclude'].str.len() == 0)
        ) &
        (parcels['camp_ownership'].str.len() > 0) &
        (parcels['year_built'] != 9999)
    ].copy()
    
    # add under utilization from:
    # https://miami.app.box.com/integrations/officeonline/openOfficeOnline?fileId=1676462145432

    # SPATIAL underutilized land

    # all parcels
    parcels['spatial'] = (parcels['building_actual_area']/parcels['lot_size'] < 0.25)

    # religious and school board exception
    parcels.loc[
        parcels['camp_ownership'].isin(["Religious", "School Board"]),
        'spatial'
    ] = (parcels['building_actual_area']/parcels['lot_size'] < 0.15)

    # MARKET underutilized land 
    # TODO

    # REGULATORY underutilized land 

    # Unincorporated Dade building density
    building_allowed = (parcels['mdc_building_density'] * parcels['lot_size']) / 43560

    # Municipal density
    municipal_density_numeric = pd.to_numeric(parcels['mdc_municipal_zone_density'], errors='coerce')
    municipal_allowed = (municipal_density_numeric * parcels['lot_size']) / 43560

    # assign to regulatory
    parcels['regulatory'] = (
        (parcels['unit_count'] < building_allowed) | 
        (parcels['unit_count'] < municipal_allowed)
    ).astype(bool)
    
    # Combine into column for categorization
    parcels['underutilized'] = ""
    parcels.loc[(parcels['spatial'] == True),'underutilized'] += "|spatial"
    parcels.loc[(parcels['regulatory'] == True),'underutilized'] += "|regulatory"
    parcels.loc[((parcels['year_built'] == 0) & (parcels['building_actual_area'] == 0)),'underutilized'] += "|vacant"
    parcels['underutilized'] = parcels['underutilized'].str[1:]
    
    # and filter out underutilized
    parcels = parcels[parcels['underutilized'].str.len() > 0].copy()

    if "json" in ext:

        def restructure(row):
            properties = {}
            for col in rename:
                if 'properties' in col:
                    prop = rename[col].upper() if rename[col] not in camp_columns else rename[col]
                    properties[prop] = row[rename[col]]
            properties['camp_ownership'] = row['camp_ownership']
            properties['camp_categories'] = row['camp_categories']
            properties['underutilized'] = row['underutilized']
            properties['spatial'] = row['spatial']
            properties['regulatory'] = row['regulatory']
            return {
                "type": "Feature",
                "properties": properties,
                "geometry": {"type": row['geometry.type'], "coordinates": row['geometry.coordinates']}
            }

        data['features'] = parcels.apply(restructure, axis=1).tolist()
        with open(f"../download/mdc_parcels_camp_ownership.json", "w") as json_file:
            json.dump(data, json_file)

    elif ext == "csv":
        parcels.to_csv(f"{path}\\ownership_{file}.csv", index=False)

if __name__ == "__main__":
    main()