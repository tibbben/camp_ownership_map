import pandas as pd
import sys
        
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
            
    return lb

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
        parcels.loc[b,'test_ownership'] = category['Ownership']
        parcels.loc[b,'test_categories'] = category['Owner Categories']

        return category['Ownership']
    
    # add columns for new categories
    parcels['test_ownership'] = ''
    parcels['test_categories'] = ''
    
    return categories.apply(filter_and_assign, parcels=parcels, axis=1)

def main():
    '''Read the parcel and categegory files and process.'''

    if len(sys.argv) == 2:
        opts=json.loads(sys.argv[1])
    else: # default for testing
        opts = {'parcel_file': 'LAND_CustomParcels_Final_2021_Tim.csv'}

    # load test parcel data and category map
    parcels = pd.read_csv(opts['parcel_file'])
    categories = pd.read_csv('OwnershipMap.csv')

    owner_filters = assign_ownership(parcels,categories)
    
    for owner_filter in owner_filters:
        print((
            f"{owner_filter} "
            f"original {len(parcels[parcels['Ownership']==owner_filter])} "
            f"test {len(parcels[parcels['test_ownership']==owner_filter])}"
        ))

if __name__ == "__main__":
    main()