import json

def parse_json(json_filename, variables):
    with open(json_filename, "r") as view_file:
        json_data = json.load(view_file)
    json_string = json.dumps(json_data)

    for key, value in variables.items():
        #Replace variables which are enclosed in curly braces
        json_string = json_string.replace("{" + key + "}", value)

    return json.loads(json_string)