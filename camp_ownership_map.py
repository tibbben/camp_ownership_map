import pandas as pd
import sys
import json

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
    "camp_ownership",
    "camp_categories",
    "shape_area",
    "shape_length"
]
        
def create_condition(owner, parcels):
    '''Create a conditional array to filter the parcels dataframe for an ownership
    category using a formatted string from the OwnsershipMap file.'''
    
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
                lb = lb & parcels['true_owner2'].str.contains(owner2s[0],na=False)
                for owner2 in owner2s[1:]:
                    lb = lb & ~parcels['true_owner2'].str.contains(owner2,na=False)
        lb = (lb)
            
    #return lb.infer_objects(copy=False)
    return lb.astype(bool).fillna(False)

def assign_ownership(parcels,categories):
    '''Assign ownership in the categories to parcels.'''
    
    def filter_and_assign(category, parcels):
        '''Filter on one ownership and assign the ownership category.'''
        
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

def exclude(parcels,exclusion):
    '''add exclusion filters to exclude column in parcels'''
    
    def filter_and_assign(exclude, parcels):
        '''filter on one exclusion and assign value to exclude'''
        
        print(exclude['Exclusion'])
        b = (parcels['camp_ownership'] == '') & \
             (parcels['true_owner1'].str.contains(exclude['Exclusion'],case=False) | \
             parcels['true_owner2'].str.contains(exclude['Exclusion'],case=False) | \
             parcels['true_owner3'].str.contains(exclude['Exclusion'],case=False) )
        b = b.astype(bool).fillna(False)
        
        parcels.loc[b,'exclude'] = f"|{exclude['Exclusion']}|" 
        
    if 'exclude' not in parcels: parcels['exclude'] = ''
    exclusion.apply(filter_and_assign, parcels=parcels, axis=1)

def main():
    '''Read the parcel and categegory files and process.'''

    if len(sys.argv) == 2:
        parcel_file = sys.argv[1]
    else: # default for testing
        base_path = "D:/Sync/gitRepos/projects/gdsc/_localdata"
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

    if "json" in ext:

        def restructure(row):
            properties = {}
            for col in rename:
                if 'properties' in col:
                    prop = rename[col].upper() if rename[col] not in camp_columns else rename[col]
                    properties[prop] = row[rename[col]]
            properties['camp_ownership'] = row['camp_ownership']
            properties['camp_categories'] = row['camp_categories']
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