# MLBB-EquipmentPlanner
Thank you for checking-out my Mobile Legends Attribute Database.

## About the Data
<br>
We have 3 datasets for you to browse:<br>
<a href="https://github.com/p3hndrx/MLBB-EquipmentPlanner/blob/master/final%20data/hero-meta-final.json">Hero Data</a><br>
<a href="https://github.com/p3hndrx/MLBB-EquipmentPlanner/blob/master/final%20data/item-meta-final.json">Item Data</a><br>
<a href="https://github.com/p3hndrx/MLBB-EquipmentPlanner/blob/master/final%20data/emblem-meta-final.json">Emblem Data</a>

## How you can Help
The data changes all the time. We constantly need to be on-top of making sure that the item, hero, and emblem stats, names, and modifiers are updated to match the data in-game. Since this data was mostly derived MANUALLY, it requires us to go in and make those changes in the datasets to match.

# Other Notes

## Default Schema
- Hero Base Attributes and Hero Metadata Schema are defined in the root/hero-meta.json
- Emblem and Item Modifiers follow the basic schema defined in root/modifiers-schema.json
- Emblem Metadata Schema is defined in root/emblem-meta.json
- Item Metadata Schema is defined in root/item-meta.json

Each of these follows the structure:

    "data":[{<br>
    ...this section repeatable per hero/item/emblem...}<br>
    ]<br>
    }


### The Proposed Calculator
When calculating basic attributes we use the formula:

    Hero Base Attributes + Emblem Modifiers + Equipment/Item Modifiers



NOTE:
At present, we are only taking into account the MAXIMUM attribute calculation.
Thus, when abilities have levels: e.g. 30 / 40 / 50 / 60 / 70 / 80, we will only calculate modifications at 80
Additionally, we are assuming that emblems are at Level 3 on all tiers.

To contribute, please make sure that you use a JSON Validator before submitting.
I recommend:
https://jsonformatter.curiousconcept.com/
