def translate_json(input_file, output_file, language):
    import json
    import googletrans

    # Read the JSON file
    with open(input_file) as f:
        data = json.load(f)

    # Create a Google Translate object
    translator = googletrans.Translator()

    # Iterate over the data
    for key, value in data.items():
        # Translate the value to the specified language
        translated_value = translator.translate(key, dest=language).text

        # Update the data
        data[key] = translated_value

    # Write the updated data to a new JSON file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
