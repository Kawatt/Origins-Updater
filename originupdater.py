import os
import re
import json
import zipfile
import shutil
from originpy import docpowers
from originpy import docactions
from originpy import docconditions

# TODO:
# [calio] Item stacks now has components field instead of tag field, which accepts an object with key-value pairs that specifies which components will be added/removed (if prefixed with !) to/from the item stack. 
# [apoli] The Powers item NBT has been converted into an `apoli:powers` item component. It also now supports an attribute modifier slot (e.g: any, mainhand, offhand, hand, feet, legs, chest, head, armor, or body) instead of an equipment slot for consistency with attribute modifiers. 
# [apoli] The Targets item NBT has been converted into an origins:origin item component. It also now works for any item that doesn't have any use actions (previously, it only worked for the Orb of Origin item.) 
# [apoli] The consuming_time_modifier(s) field(s) of the edible_item power type has been moved to the modify_food power type and renamed to eat_ticks_modifier(s) for consistency.
# Items stacks im missing pretty sure
# Update pack format
# [apoli] Removed the material block condition type since it has been deprecated for quite some time (since 1.20.) Use block tags to classify blocks in their own groups/materials and use the in_tag block condition type instead.
# [apoli] Removed any fields/types that use the legacy damage source data type since it has been deprecated for quite some time (since 1.19.4.) Use damage types and vanilla damage type tags to control the properties of a damage source. Partly done
# [apoli] Removed the client and server boolean fields from the add_velocity entity/bi-entity action types since its usage is redundant. Use the side meta action type instead.
# Texture id changes


def log(type, trace, text):
    file = ""
    if "file" in trace:
        file = trace["file"]
    if "fields" in trace and trace["fields"] != "":
        fields = trace["fields"]
        print("[" + type + "] " + "File: " + file + " in " + fields + ": " + text) 
    else:
        print("[" + type + "] " + "File: " + file + ": " + text) 

def rename_key(d, old_key, new_key):
    """Renames a key in a dictionary."""
    if old_key in d:
        d[new_key] = d.pop(old_key)
    return d

def get_items_from_folder(folder_path):
    """Returns a list of folders and another of files inside the given folder."""
    files = []
    folders = []
    with os.scandir(folder_path) as entries:
        for entry in entries:
            if entry.is_file():
                files.append(entry.name)
            elif entry.is_dir():
                folders.append(entry.name)
    return folders, files

def get_items_from_all_folders(folder_path):
    """
    Returns a list of folders and a list of files for all directories
    inside folder_path.
    """
    retfiles = []
    retfolders = []
    for root, folders, files in os.walk(folder_path):
        for file in files:
            retfiles.append(os.path.join(root, file))
        for folder in folders:
            retfolders.append(os.path.join(root, folder))
    return retfolders, retfiles

def read_json_file(file_path):
    """Returns a dict of the json"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json_file(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def is_datapack_valid(folder_path):
    """Returns true if the datapack has a data folder and pack.mcmeta file"""
    folders, files = get_items_from_folder(folder_path)

    error = 0
    if not "data" in folders:
        print("'data' folder not found")
        error += 1
    
    if not "pack.mcmeta" in files:
        print("'pack.mcmeta' file not found")
        error += 1

    if error > 0:
        return False
    else:
        return True
    
def is_json_object(data):
    if isinstance(data, dict):
        return True
    else:
        return False

def get_type(json_data):
    type = json_data["type"]

    if type.startswith("apoli:"):
        type.replace("apoli:", "origins:", 1)
    
    return type

def unzip_datapack(zip, extracted):
    """Unzips the zip."""
    # Check if folder already exists
    if os.path.exists(extracted):
        answer = input(f"Folder '{extracted}' already exists. Overwrite? (y/n): ").strip().lower()
        if answer != "y":
            print("Extraction canceled.")
            return
        shutil.rmtree(extracted)  # remove old folder
    # Unzip
    try:
        with zipfile.ZipFile(zip, "r") as zip_ref:
            zip_ref.extractall(extracted)
        print(f"Extracted '{zip}' into '{extracted}'")
    except zipfile.BadZipFile:
        print(f"'{zip}' is not a valid ZIP file")

def get_namespaces(folder_path):
    folders, _ = get_items_from_folder(folder_path)
    return folders

def fix_damage(trace, type, json_data): 
    if "damage_type" not in json_data:
        if "source" in json_data:
            #TODO: Add the damage type to the tag directly, and make damage type directly. Detect existing damage types.
            log("WARNING", trace, "Fixing damage types is unimplemented.")
        else:
            log("ERROR", trace, "Couldn't find damage source")


def fix_meta_action(trace, type, json_data):
    if type == "origins:chance":
        if "action" in json_data:
            json_data = rename_key(json_data, "action", "success_action")
            log("INFO", trace, "Renamed action to success_action")

def fix_entity_action(trace, json_data):
    type = get_type(json_data)
    if type in docactions.meta_actions:
        fix_meta_action(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docactions.meta_actions, "Entity")
    elif type in docactions.entity_actions:
        iterate_through_fields(trace.copy(), type, json_data, docactions.entity_actions)
        if type == "origins:action_on_set":
            json_data["type"] = "origins:action_on_entity_set"
            log("INFO", trace, "Renamed action_on_set to action_on_entity_set")
        # This has to be after the iteration so the effects update
        if type == "origins:spawn_effect_cloud":
            if "effect" in json_data:
                effect = json_data.pop("effect")
                json_data["effect_component"] = {"custom_effects": [effect]}
            elif "effects" in json_data:
                effects = json_data.pop("effects")
                json_data["effect_component"] = {"custom_effects": effects}
            log("INFO", trace, "Updated action spawn effect cloud to use components")
        if type == "origins:damage":
            fix_damage(trace, type, json_data)

def fix_bientity_action(trace, json_data):
    type = get_type(json_data)
    if type in docactions.meta_actions:
        fix_meta_action(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docactions.meta_actions, "Bi-entity")
    elif type in docactions.bientity_actions:
        iterate_through_fields(trace.copy(), type, json_data, docactions.bientity_actions)
        if type == "origins:add_to_set":
            json_data["type"] = "origins:add_to_entity_set"
            log("INFO", trace, "Renamed add_to_set to add_to_entity_set")
        if type == "origins:remove_from_set":
            json_data["type"] = "origins:remove_from_entity_set"
            log("INFO", trace, "Renamed remove_from_set to remove_from_entity_set")
        if type == "origins:damage":
            fix_damage(trace, type, json_data)

def fix_block_action(trace, json_data):
    type = get_type(json_data)
    if type in docactions.meta_actions:
        fix_meta_action(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docactions.meta_actions, "Block")
    elif type in docactions.block_actions:
        iterate_through_fields(trace.copy(), type, json_data, docactions.block_actions)

def fix_item_action(trace, json_data):
    type = get_type(json_data)
    if type in docactions.meta_actions:
        fix_meta_action(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docactions.meta_actions, "Item")
    elif type in docactions.item_actions:
        iterate_through_fields(trace.copy(), type, json_data, docactions.item_actions)
        if type == "origins:merge_nbt":
            json_data["type"] = "origins:merge_custom_data"
            log("INFO", trace, "Renamed item action type merge_nbt to merge_custom_data")

def fix_meta_condition(trace, type, json_data):
    pass

def fix_entity_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Entity")
    elif type in docconditions.entity_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.entity_conditions)
        if type == "origins:entity_group":
            log("INFO", trace, "Changing entity_group condition for an in_tag condition.")
            json_data["type"] = "origins:in_tag",
            if json_data["group"].endswith("undead"):
                json_data["group"] = "minecraft:undead"
            elif json_data["group"].endswith("aquatic"):
                json_data["group"] = "minecraft:aquatic"
            elif json_data["group"].endswith("arthropod"):
                json_data["group"] = "minecraft:arthropod"
            elif json_data["group"].endswith("illager"):
                json_data["group"] = "minecraft:illager"
            else:
                log("ERROR", trace, "Entity Group not found, was unable to find correct tag.")
            json_data = rename_key(json_data, "group", "tag")
        if type == "origins:set_size":
            json_data["type"] = "origins:entity_set_size"
            log("INFO", trace, "Renamed set_size to entity_set_size")

def fix_bientity_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Bi-entity")
    elif type in docconditions.bientity_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.bientity_conditions)
        if type == "origins:in_set":
            json_data["type"] = "origins:in_entity_set"
            log("INFO", trace, "Renamed in_set to in_entity_set")

def fix_block_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Block")
    elif type in docconditions.block_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.block_conditions)
        if type == "origins:replacable":
            json_data["type"] = "origins:replaceable"
            log("INFO", trace, "Renamed replacable block condition to replaceable (typo)")
        if type == "origins:material":
            log("ERROR", trace, "Material condition fix not implemented, see https://origins.readthedocs.io/en/latest/types/data_types/material/ for how to fix it")

def fix_item_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Item")
    elif type in docconditions.item_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.item_conditions)
        if type == "origins:harvest_level":
            # TODO: i need to know where to create the folder tags
            # https://minecraft.wiki/w/Tiers
            # Remember it may require multiple tags (>1 are harvest levels of 2, 3 and 4)
            log("WARNING", trace, "Harvest levels don't exsist anymore.")
            log("ERROR", trace, "Fixing harvest level condition is unimplemented.")
        elif type == "origins:nbt":
            json_data["type"] = "origins:custom_data"
            log("INFO", trace, "Renamed nbt item condition to custom_data")
            log("ERROR", trace, "Fixing nbt/custom_data condition is unimplemented.")
            #TODO: perhaps modify the nbt
        elif type == "origins:meat":
            json_data["type"] = "origins:ingredient",
            json_data["ingredient"] = {"tag": "minecraft:wolf_food"}
            log("INFO", trace, "Updated meat item condition to use the minecraft:wolf_food tag instead")
        if type == "origins:is_damageable":
            json_data["type"] = "origins:damageable"
            log("INFO", trace, "Renamed is_damageable to damageable")
        if type == "origins:is_equippable":
            json_data["type"] = "origins:equippable"
            log("INFO", trace, "Renamed is_equippable to equippable")
        if type == "origins:fireproof":
            json_data["type"] = "origins:fire_resistant"
            log("INFO", trace, "Renamed fireproof to fire_resistant")


def fix_damage_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Damage")
    elif type in docconditions.damage_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.damage_conditions)

def fix_biome_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Biome")
    elif type in docconditions.biome_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.biome_conditions)
        if type == "origins:category":
            if json_data["category"] == "beach":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_beach"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category beach to minecraft:is_beach tag")
            elif json_data["category"] == "desert":
                json_data.pop("category")
                json_data["tag"] = "c:desert"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category desert to c:desert tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "extreme_hills":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_hill"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category extreme_hills to minecraft:is_hill tag")
            elif json_data["category"] == "forest":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_forest"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category forest to minecraft:is_forest tag")
            elif json_data["category"] == "icy":
                json_data.pop("category")
                json_data["tag"] = "c:is_icy"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category icy to c:is_icy tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "jungle":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_jungle"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category jungle to minecraft:is_jungle tag")
            elif json_data["category"] == "mesa":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_badlands"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category mesa to minecraft:is_badlands tag")
            elif json_data["category"] == "mountain":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_mountain"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category mountain to minecraft:is_mountain tag")
            elif json_data["category"] == "mushroom":
                json_data.pop("category")
                json_data["tag"] = "c:is_mushroom"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category mushroom to c:is_mushroom tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "nether":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_nether"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category nether to minecraft:is_nether tag")
            elif json_data["category"] == "none":
                json_data.pop("category")
                json_data["tag"] = "c:is_void"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category none to c:is_void tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "ocean":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_ocean"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category ocean to minecraft:is_ocean tag")
            elif json_data["category"] == "plains":
                json_data.pop("category")
                json_data["tag"] = "c:is_plains"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category plains to c:is_plains tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "river":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_river"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category river to minecraft:is_river tag")
            elif json_data["category"] == "savanna":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_savanna"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category savanna to minecraft:is_savanna tag")
            elif json_data["category"] == "swamp":
                json_data.pop("category")
                json_data["tag"] = "c:is_swamp"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category swamp to c:is_swamp tag")
                log("WARNING", trace, "This tag will only work on fabric")
            elif json_data["category"] == "taiga":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_taiga"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category taiga to minecraft:is_taiga tag")
            elif json_data["category"] == "the_end":
                json_data.pop("category")
                json_data["tag"] = "minecraft:is_end"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category the_end to minecraft:is_end tag")
            elif json_data["category"] == "underground":
                json_data.pop("category")
                json_data["tag"] = "c:is_underground"
                json_data["type"] = "origins:in_tag"
                log("INFO", trace, "Updated biome category underground to c:is_underground tag")
                log("WARNING", trace, "This tag will only work on fabric")

def fix_fluid_condition(trace, json_data):
    type = get_type(json_data)
    if type in docconditions.meta_conditions:
        fix_meta_condition(trace.copy(), type, json_data)
        iterate_through_fields(trace.copy(), type, json_data, docconditions.meta_conditions, "Fluid")
    elif type in docconditions.fluid_conditions:
        iterate_through_fields(trace.copy(), type, json_data, docconditions.fluid_conditions)

def fix_attribute(trace, json_data):
    if "reach-entity-attributes:attack_range" in json_data["attribute"]:
        json_data["attribute"] = json_data["attribute"].replace("reach-entity-attributes:attack_range", "minecraft:player.entity_interaction_range", 1)
        log("INFO", trace, "Updated attack range attribute to work without the mod Reach Entity Attributes")
    if "reach-entity-attributes:reach" in json_data["attribute"]:
        json_data["attribute"] = json_data["attribute"].replace("reach-entity-attributes:reach", "minecraft:player.block_interaction_range", 1)
        log("INFO", trace, "Updated reach attribute to work without the mod Reach Entity Attributes")

def fix_operation(trace, json_data):
    if "addition" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("addition", "add_value", 1)
        log("INFO", trace, "Renamed operation addition to add_value")
    elif "multiply_base" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("multiply_base", "add_multiplied_base", 1)
        log("INFO", trace, "Renamed operation multiply_base to add_multiplied_base")
    elif "multiply_total" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("multiply_total", "add_multiplied_total", 1)
        log("INFO", trace, "Renamed operation multiply_total to add_multiplied_total")

def fix_attributed_operation(trace, json_data):
    if "addition" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("addition", "add_base_early", 1)
        log("INFO", trace, "Renamed operation addition to add_base_early")
    elif "multiply_base" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("multiply_base", "multiply_base_additive", 1)
        log("INFO", trace, "Renamed operation multiply_base to multiply_base_additive")
    elif "multiply_total" == json_data["operation"]:
        json_data["operation"] = json_data["operation"].replace("multiply_total", "multiply_total_multiplicative", 1)
        log("INFO", trace, "Renamed operation multiply_total to multiply_total_multiplicative")

def fix_value(trace, json_data):
    if "value" in json_data:
        json_data = rename_key(json_data, "value", "amount")
        log("INFO", trace, "Renamed value to amount")
    
def fix_attribute_modifier(trace, json_data):
    fix_attributed_operation(trace, json_data)
    fix_value(trace,json_data)

def fix_attributed_attribute_modifier(trace, json_data):
    fix_attribute(trace, json_data)
    if not "id" in json_data:
        id = trace["namespace"] + ":" + os.path.basename(trace["file"]).removesuffix(".json")
        json_data["id"] = id
        log("INFO", trace, "Added id " + id + " to attributed attribute modifier")
    fix_operation(trace, json_data)
    fix_value(trace,json_data)

def fix_status_effect_instance(trace, json_data):
    if "effect" in json_data:
        json_data = rename_key(json_data, "effect", "id")
        log("INFO", trace, "Renamed effect to id")
    if "is_ambient" in json_data:
        json_data = rename_key(json_data, "is_ambient", "ambient")
        log("INFO", trace, "Renamed is_ambient to ambient")

def fix_food_component(trace, json_data):
    if "hunger" in json_data:
        json_data = rename_key(json_data, "hunger", "saturation")
    if "always_edible" in json_data:
        json_data = rename_key(json_data, "always_edible", "can_always_eat")
    if "snack" in json_data and json_data["snack"]:
        json_data.pop("snack")
        json_data["eat_seconds"] = 0.8

def fix_crafting_recipe(trace, json_data):
    log("ERROR", trace, "Fixing crafting recipes is unimplemented.")

def fix_particle_effect(trace, json_data):
    old_params = json_data['params']

    if json_data['type'] in {"block", "minecraft:block", "block_marker", "minecraft:block_marker", "falling_dust", "minecraft:falling_dust"}:
        pattern_blockstate = re.compile(r"^(?P<block>[a-z0-9/:._-]+)(?:\[(?P<props>[a-z0-9/._-]+=[a-z0-9/._-]+(?:,\s+[a-z0-9/._-]+=[a-z0-9/._-]+)*)])?$")
        pattern_props = re.compile(r"(?P<property>[a-z0-9/._-]+)=(?P<value>[a-z0-9/._-]+)")

        match = pattern_blockstate.match(old_params)
        block = match.group("block")
        prop_str = match.group("props")
        new_params = {"block_state": {"Name": block}}
        if prop_str:
            properties = {}
            for prop_match in pattern_props.finditer(prop_str):
                state = prop_match.groupdict()
                if state["value"] == 'true':
                    state["value"] = True
                elif state["value"] == 'false':
                    state["value"] = False
                elif state["value"].isnumeric():
                    state["value"] = float(state["value"])

                properties.update({state["property"]: state['value']})
            new_params["Properties"] = properties

    elif json_data['type'] in {'dragon_breath', 'minecraft:dragon_breath'}:
        new_params = {"power": float(old_params)}

    elif json_data['type'] in {"dust", "minecraft:dust"}:
        pattern = re.compile(r"(?P<red>\d(\.\d+)?) (?P<green>\d(\.\d+)?) (?P<blue>\d(\.\d+)?) (?P<scale>\d(\.\d+)?)")
        groups = pattern.match(old_params).groupdict()
        new_params = {
            "color": [
                float(groups['red']),
                float(groups['green']),
                float(groups['blue'])
            ],
            "scale": float(groups['scale'])
        }

    elif json_data['type'] in {"dust_color_transition", "minecraft:dust_color_transition"}:
        pattern = re.compile(r"(?P<from_red>\d(\.\d+)?) (?P<from_green>\d(\.\d+)?) (?P<from_blue>\d(\.\d+)?) (?P<scale>\d(\.\d+)?) (?P<to_red>\d(\.\d+)?) (?P<to_green>\d(\.\d+)?) (?P<to_blue>\d(\.\d+)?)")  # Ugly...
        groups = pattern.match(old_params).groupdict()
        new_params = {
            "from_color": [
                float(groups['from_red']),
                float(groups['from_green']),
                float(groups['from_blue'])
            ],
            "to_color":   [
                float(groups['to_red']),
                float(groups['to_green']),
                float(groups['to_blue'])
            ],
            "scale":      float(groups['scale'])
        }

    elif json_data['type'] in {"item", "minecraft:item"}:
        new_params = {"item": {"id": old_params}}

    elif json_data['type'] in {"sculk_charge", "minecraft:sculk_charge"}:
        new_params = {"roll": float(old_params)}

    elif json_data['type'] in {"shriek", "minecraft:shriek"}:
        new_params = {"delay": float(old_params)}

    elif json_data['type'] in {"vibration", "minecraft:vibration"}:
        pattern = re.compile(r"(?P<posX>\d+(\.\d+)?) (?P<posY>\d+(\.\d+)?) (?P<posZ>\d+(\.\d+)?) (?P<delay>\d+(\.\d+)?)")
        groups = pattern.match(old_params).groupdict()
        new_params = {"destination": {"type": "block", "pos": [float(groups['posX']), float(groups['posY']), float(groups['posZ'])]}, "arrival_in_ticks": float(groups['delay'])}

    else:
        new_params = old_params  # Fallback

    json_data["params"] = new_params
    log("INFO", trace, f'Updated params for "{json_data["type"]}" particle.')


def select_type(trace, type, field_data, meta_type = None):
    if type == "Entity Action Type" and is_json_object(field_data):
        fix_entity_action(trace.copy(), field_data)
    if type == "Bi-entity Action Type" and is_json_object(field_data):
        fix_bientity_action(trace.copy(), field_data)
    if type == "Block Action Type" and is_json_object(field_data):
        fix_block_action(trace.copy(), field_data)
    if type == "Item Action Type" and is_json_object(field_data):
        fix_item_action(trace.copy(), field_data)
    if type == "Entity Condition Type" and is_json_object(field_data):
        fix_entity_condition(trace.copy(), field_data)
    if type == "Bi-entity Condition Type" and is_json_object(field_data):
        fix_bientity_condition(trace.copy(), field_data)
    if type == "Block Condition Type" and is_json_object(field_data):
        fix_block_condition(trace.copy(), field_data)
    if type == "Item Condition Type" and is_json_object(field_data):
        fix_item_condition(trace.copy(), field_data)
    if type == "Damage Condition Type" and is_json_object(field_data):
        fix_damage_condition(trace.copy(), field_data)
    if type == "Biome Condition Type" and is_json_object(field_data):
        fix_biome_condition(trace.copy(), field_data)
    if type == "Fluid Condition Type" and is_json_object(field_data):
        fix_fluid_condition(trace.copy(), field_data)
    if type == "Attribute Modifier" and is_json_object(field_data):
        fix_attribute_modifier(trace.copy(), field_data)
    if type == "Attributed Attribute Modifier" and is_json_object(field_data):
        fix_attributed_attribute_modifier(trace.copy(), field_data)
    if type == "Status Effect Instance" and is_json_object(field_data):
        fix_status_effect_instance(trace.copy(), field_data)
    if type == "Food Component" and is_json_object(field_data):
        fix_food_component(trace.copy(), field_data)
    if type == "Crafting Recipe" and is_json_object(field_data):
        fix_crafting_recipe(trace.copy(), field_data)
    if type == "Particle Effect" and is_json_object(field_data):
        fix_particle_effect(trace.copy(), field_data)
    if type == "Action Type" and is_json_object(field_data):
        select_type(trace, meta_type + " Action Type", field_data)
    if type == "Condition Type" and is_json_object(field_data):
        select_type(trace, meta_type + " Condition Type", field_data)


# Its given a list of dicts that indicate if the field is an array and what type it is
# then fixes it
def find_allowed_types(trace, allowed_types, field_data, meta_type = None):
    for typ in allowed_types:
        if typ["is_array"]:
            for i, object in enumerate(field_data):
                new_trace = trace.copy()
                new_trace["fields"] = new_trace["fields"] + "[" + str(i) + "]"
                select_type(new_trace, typ["type"], object, meta_type)
        else:
            select_type(trace.copy(), typ["type"], field_data, meta_type)
    return field_data

# Detects the type and iterates through that type's fields, fixing each
def iterate_through_fields(trace, type, json_data, shape_data, meta_type = None):
    if type in shape_data:
        shape = shape_data[type]
        # Iterate through every field of the power definition
        for field in shape:
            # Check if the field is even in the actual power
            # Could be done the other way around, but i dont want to parse non-existing fields
            field_name = field["name"]
            new_trace = trace.copy()
            if field_name in json_data:
                new_trace["fields"] = new_trace["fields"] + "." + field_name
                field_data = json_data[field_name]
                # Check what types are allowed for the field
                field_data = find_allowed_types(new_trace.copy(), field["type"], field_data, meta_type)
                json_data[field_name] = field_data
    else:
        log("ERROR", trace, "Field " + type + " does not exist or belongs to an addon.")

def fix_power(trace, json_data):
    log("INFO", trace, "Fixing power")
    type = get_type(json_data)
    if "condition" in json_data:
        condition = json_data["condition"]
        fix_entity_condition(trace, condition)
        json_data["condition"] = condition
    if type == "origins:overlay":
        if "texture" in json_data:
            #path = os.path(json_data["texture"])
            #namespace = path.parts[1]
            #name = path.stem
            #id = f"{namespace}:{name}"
            #json_data["texture"] = id
            #log("INFO", trace, "Renamed location of texture to " + id + ", make sure the texture is in assets/" + namespace + "/textures/overlay/sprites/" + name + ".png")
            log("ERROR", trace, "Overlay texture change not implemented (if even necessary)")

    iterate_through_fields(trace.copy(), type, json_data, docpowers.powers)

    if type == "origins:entity_group":
        json_data["type"] = "origins:modify_type_tag"
        if json_data["group"].endswith("undead"):
            json_data["group"] = "minecraft:undead"
        elif json_data["group"].endswith("aquatic"):
            json_data["group"] = "minecraft:aquatic"
        elif json_data["group"].endswith("arthropod"):
            json_data["group"] = "minecraft:arthropod"
        elif json_data["group"].endswith("illager"):
            json_data["group"] = "minecraft:illager"
        else:
            log("ERROR", trace, "Entity Group not found, was unable to find correct tag.")
        json_data = rename_key(json_data, "group", "tag")

def update_powers(trace, folder_path):
    _, files = get_items_from_all_folders(folder_path)
    for file in files:
        trace["file"] = file
        json_data = read_json_file(file)

        type = get_type(json_data)
        trace["fields"] = ""
        if type == "origins:multiple":
            shape = docpowers.powers[type]
            for field_name in json_data:
                new_trace = trace.copy()
                if field_name not in shape and field_name not in docpowers.power:
                    new_trace["fields"] = new_trace["fields"] + "." + field_name
                    field_data = json_data[field_name]
                    fix_power(new_trace, field_data)
                    json_data[field_name] = field_data
        else:
            fix_power(trace.copy(), json_data)

        write_json_file(file, json_data)

def fix_item_stack(trace, stack):
    stack = rename_key(stack, "item", "id")
    if "amount" in stack:
        stack = rename_key(stack, "amount", "count")
    if "tag" in stack:
        # TODO: handle nbt tag
        log("ERROR", trace, "Fixing nbt tags is unimplemented.")
    return stack

def fix_icon(trace, origin):
    icon = origin["icon"]
    # Convert icon to object
    if isinstance(icon, str):
        icon = {'item': icon}
    origin["icon"] = fix_item_stack(trace.copy(), icon)
    return origin

def update_origins(trace, folder_path):
    _, files = get_items_from_all_folders(folder_path)
    for file in files:
        trace["file"] = file
        origin = read_json_file(file)
        origin = fix_icon(trace.copy(), origin)
        write_json_file(file, origin)

def update_folders(trace, path):
    folders, _ = get_items_from_folder(path)
    if "tags" in folders:
        tagfolder = os.path.join(path, "tags")
        tagfolders, _ = get_items_from_folder(tagfolder)
        if "items" in tagfolders:
            os.rename(os.path.join(tagfolder, "items"), os.path.join(tagfolder, "item"))
            log("INFO", trace, "Renamed folder tags/items to tags/item")
        if "blocks" in tagfolders:
            os.rename(os.path.join(tagfolder, "blocks"), os.path.join(tagfolder, "block"))
            log("INFO", trace, "Renamed folder tags/blocks to tags/block")
        if "entity_types" in tagfolders:
            os.rename(os.path.join(tagfolder, "entity_types"), os.path.join(tagfolder, "entity_type"))
            log("INFO", trace, "Renamed folder tags/entity_types to tags/entity_type")
        if "fluids" in tagfolders:
            os.rename(os.path.join(tagfolder, "fluids"), os.path.join(tagfolder, "fluid"))
            log("INFO", trace, "Renamed folder tags/fluids to tags/fluid")
        if "game_events" in tagfolders:
            os.rename(os.path.join(tagfolder, "game_events"), os.path.join(tagfolder, "game_event"))
            log("INFO", trace, "Renamed folder tags/game_events to tags/game_event")
        if "functions" in tagfolders:
            os.rename(os.path.join(tagfolder, "functions"), os.path.join(tagfolder, "function"))
            log("INFO", trace, "Renamed folder tags/functions to tags/function")
    if "structures" in folders:
        os.rename(os.path.join(path, "structures"), os.path.join(path, "structure"))
        log("INFO", trace, "Renamed folder structures to structure")
    if "advancements" in folders:
        os.rename(os.path.join(path, "advancements"), os.path.join(path, "advancement"))
        log("INFO", trace, "Renamed folder advancements to advancement")
    if "recipes" in folders:
        os.rename(os.path.join(path, "recipes"), os.path.join(path, "recipe"))
        log("INFO", trace, "Renamed folder recipes to recipe")
    if "loot_tables" in folders:
        os.rename(os.path.join(path, "loot_tables"), os.path.join(path, "loot_table"))
        log("INFO", trace, "Renamed folder loot_tables to loot_table")
    if "predicates" in folders:
        os.rename(os.path.join(path, "predicates"), os.path.join(path, "predicate"))
        log("INFO", trace, "Renamed folder predicates to predicate")
    if "item_modifiers" in folders:
        os.rename(os.path.join(path, "item_modifiers"), os.path.join(path, "item_modifier"))
        log("INFO", trace, "Renamed folder item_modifiers to item_modifier")
    if "functions" in folders:
        os.rename(os.path.join(path, "functions"), os.path.join(path, "function"))
        log("INFO", trace, "Renamed folder functions to function")

def start_updating(folder_path):
    if not is_datapack_valid(folder_path):
        return
    data_path = os.path.join(folder_path,"data")
    namespaces = get_namespaces(data_path)
    trace = {}
    trace["data_folder"] = data_path
    
    # Update each namespace
    for namespace in namespaces:
        path = os.path.join(data_path, namespace)
        trace["namespace"] = namespace
        update_powers(trace.copy(), os.path.join(path,"powers"))
        update_origins(trace.copy(), os.path.join(path,"origins"))
        update_folders(trace.copy(), path)

def open_datapack():
    folder = input("Enter the folder path: ").strip()
    # If .zip is specified, open the zip
    if folder.endswith(".zip") and os.path.isfile(folder):
        zip_path = folder
        folder, _ = os.path.splitext(folder)
        unzip_datapack(zip_path, folder)
    # Try opening the folder
    if os.path.isdir(folder):
        start_updating(folder)
    # Check for zip again
    else:
        zip_path = f"{folder}.zip"
        if os.path.isfile(zip_path):
            unzip_datapack(zip_path, folder)
            if os.path.isdir(folder):
                start_updating(folder)
        else:
            print("Invalid folder path.")

if __name__ == "__main__":
    open_datapack()
