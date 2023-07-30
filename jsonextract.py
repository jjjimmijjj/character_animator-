import os
import json

def separate_chat_data(json_data):
    friendly_interactions = []
    romantic_fantasy_roleplay = []
    inappropriate_offensive_content = []
    miscellaneous_responses = []

    data_list = json_data.get("data", [])

    for item in data_list:
        message, response = item
        if message and response:
            # Separate data into different categories based on keywords in the message
            if any(keyword in message.lower() for keyword in ["hello", "hey", "hi"]):
                friendly_interactions.append(item)
            elif any(keyword in message.lower() for keyword in ["character sheet", "help"]):
                romantic_fantasy_roleplay.append(item)
            elif any(keyword in message.lower() for keyword in ["lousy", "insolence", "spank"]):
                inappropriate_offensive_content.append(item)
            else:
                miscellaneous_responses.append(item)

    return {
        "Friendly Interaction and Confusion": friendly_interactions,
        "Romantic and Fantasy Roleplay": romantic_fantasy_roleplay,
        "Inappropriate and Offensive Content": inappropriate_offensive_content,
        "Random and Miscellaneous Responses": miscellaneous_responses
    }

if __name__ == "__main__":
    # Function to combine JSON files and extract chat data
    def combine_and_extract_data(folder_path, output_file):
        # Initialize an empty list to store all the data from JSON files
        combined_data = []

        # Iterate through all the files in the folder
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and filename.lower().endswith('.json'):
                # Read data from each JSON file and append it to the combined_data list
                with open(filepath, 'r') as file:
                    try:
                        json_data = json.load(file)
                        separated_data = separate_chat_data(json_data)
                        combined_data.append(separated_data)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON in file: {filepath}")

        # Write the combined data to the output file
        with open(output_file, 'w') as outfile:
            json.dump(combined_data, outfile, indent=2)

        print(f"Successfully combined and extracted chat data from {len(combined_data)} JSON files into {output_file}")

    folder_path = r"F:\oogabooga\oobabooga_windows\text-generation-webui\text-generation-webui\logs"
    output_file = "combined_logs_with_separated_data.json"

    combine_and_extract_data(folder_path, output_file)
