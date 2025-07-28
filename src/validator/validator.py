import os
import json
from jsonschema import validate, ValidationError, SchemaError

class Validator:
    def __init__(self):
        """
        Simple Validator. No schema is loaded at init.
        """
        pass

    def validate_json_file(self, 
                           file_path: str, 
                           schema_filename: str = None
                           ) -> bool:
        """
        Validates that a file:
        - Exists
        - Can be parsed as valid JSON
        - (Optionally) conforms to a JSON Schema, if schema_filename is provided

        :param file_path: Path to the JSON file.
        :param schema_filename: Path to the schema file (optional).
        :return: True if valid, otherwise raises an error.
        """
        # Try to read and parse the JSON
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        # If no schema is provided, just return True (file is readable)
        if not schema_filename:
            print(f"JSON file '{os.path.basename(file_path)}' is valid.")
            return True

        # Try to read the schema file
        if not os.path.isfile(schema_filename):
            raise FileNotFoundError(f"Schema file not found: {schema_filename}")

        try:
            with open(schema_filename, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Schema file is not valid JSON: {e}")

        # Validate the data using the schema
        try:
            validate(instance=data, schema=schema)
        except ValidationError as ve:
            raise ValueError(f"JSON does not conform to schema:\n{ve.message}")
        except SchemaError as se:
            raise ValueError(f"Schema is invalid:\n{se.message}")
        print(f"JSON file '{os.path.basename(file_path)}' is valid and conforms to the schema '{os.path.basename(schema_filename)}'.")
        return True

validator = Validator()
validator.validate_json_file(
    r"C:\Users\brend\Documents\Coding Projects\alexandria_media_manager\config\alexandria_drives.config",
    r"C:\Users\brend\Documents\Coding Projects\alexandria_media_manager\src\validator\schemas\schema_alexandria_config.json")
