
## CAMP Ownership Mapping

The code and data in this repo are used to assign specific ownership names and ownership categories to property parcels in Miami-Dade County according to criteria created by the University of Miami [Office for Community and Civic Engagement](https://civic.miami.edu/).

### Use
```bash
python camp_ownership_map.py <parcel_file.csv>
```

### Inputs

- OwnershipMap.csv
- parcel_file.csv

### OwnershipMap.csv

this is a five column csv file:
| Ownership     | true_owner[123] | Owner Categories  | dor_code_cur    | notes        |
|:--------------|:----------------|:------------------|:----------------|:-------------|
| Organization Name/Type | `<filter expression>` | Owner Category | not used | notes |

The `<filter expression>` is constructed as follows:
| Filter              | Action            |
|:--------------------| :---------------- 
| `MATCH TEXT[|...][|...]` | Contains MATCH TEXT in true_owner_1 |
| `MATCH TEXT!NOT MATCH TEXT[|...][|...]` | Contains MATCH TEXT in true_owner_1 `AND` does not contain NOT MATCH TEXT in true_owner_1 |
| `MATCH TRUE&&MATCH TEXT 2[|...][|...]` | Contains MATCH TEXT in true_owner_1 `AND` contains MATCH TEXT 2 in true_owner_2|
| `MATCH TEXT&&!NOT MATCH TEXT 2[|...][|...]` | Contains MATCH TEXT in true_owner_1 `AND` does not contain NOT MATCH TEXT 2 in true_owner_2|

notes:
- logic is always `OR` for lists delimited by the `|` character 
- match text for true_owner_1 can be blank with `&&`; `&&MATCH` means anything in true_owner_1 `AND` MATCH in true_owner_2
- `!` can be chained as long as needed
- there is no match on true_owner_3

diagram for entire data pipeline from parcels to ownership:
```mermaid
flowchart  TD
A[Parcels] -->|mdc_property_boundary, mdc_municipal_zoning, mdc_county_zoning, mdc_flood_hazard, mdc_qualified_opportunity_zones, mdc_neighborhoods, mdc_municipal_boundary, com_neighborhoods, mdc_2015_dem_30ft| B(Parcel Vector Tiles)
X(mdc_cce_distinct_dor_codes)  --> B
C[mdc_cce_land_parcel_filters] --> D
B  --> |mdc_major_roads, mdc_streets, mdc_urban_growth_boundary, mdc_municipal_park_boundaries, mdc_county_park_boundaries, mdc_state_and_national_parks| D(CAMP Parcels)
Y(mdc_cce_land_exclude_water)  --> D
Z(mdc_cce_land_exclude_dor_codes)  --> D
D  -->|Filters| H(CAMP Parcels Filtered)
H  --> |Owner  Filters| F(CAMP Parcels with Ownership)
```

