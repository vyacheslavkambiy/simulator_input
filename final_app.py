import json
import os
import streamlit as st
from geopy.geocoders import Nominatim
import random
import pandas as pd
import requests
from datetime import datetime   #generate a unique filename for each JSON file, by appending a timestamp to the filename
from azure.storage.blob import BlobServiceClient

from azure.identity import DefaultAzureCredential  # Import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Set page title
st.title("Älykkäät Tyhjentaminen App")
st.write("Input data for simulation:")
col1, col2 = st.columns(2)
with col1: 
    sim_runtime_days = st.number_input("# Simulation runtime (in days)", min_value=1, step=1)
    load_capacity = st.number_input("load capacity, Tonnes", min_value=1.0, step=0.1)
    max_route_duration = st.number_input("max route duration per day , in Minutes (9h - 45min break = 495min)", min_value=1, step=1) 
    #depots = st.number_input("# number of depots", min_value=1, step=1)
with col2:
    break_duration = st.number_input("break duration, Minutes #Break Happens after 1/2 of drivetime", min_value=1, step=1)
    num_breaks_per_shift = st.number_input("numbers of brakes per shift", min_value=1, step=1)
    pickup_duration = st.number_input("pickup duration  time, Minutes", min_value=1, step=1) 


# Generate a unique filename with a timestamp
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
json_filename = f"input_data_{timestamp}.json"
# Fetch the Azure Blob Storage connection string from Azure Key Vault using DefaultAzureCredential
vault_url = "https://keyvaultforhamk.vault.azure.net/"
secret_name = "inputdatatoazureblob"  # Replace with the name of your secret
credential = DefaultAzureCredential()
key_vault_secret = SecretClient(vault_url=vault_url, credential=credential).get_secret(secret_name)
# Use the fetched connection string
connection_string = key_vault_secret.value
container_name = "inputdata"
blob_name = json_filename
# Upload the JSON file to Azure Blob Storage
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)




# Show a "Save Input Data" button
if st.button("Save Input Data to blob"):
    # Create a dictionary to store the input data
    input_data = {
        "sim_runtime_days": sim_runtime_days,
        "load_capacity": load_capacity,
        "max_route_duration": max_route_duration,
        "break_duration": break_duration,
        "num_breaks_per_shift": num_breaks_per_shift,
        "pickup_duration": pickup_duration,
        #"depots": depots 
    }

  
# Save the input data as a JSON file locally
    # Uncomment the following lines if you want to save the JSON file locally
    # with open(json_filename, "w") as json_file:
    #     json.dump(input_data, json_file, indent=4)

# This part to Upload the JSON string directly to Azure Blob Storage
    blob_client.upload_blob(json.dumps(input_data, indent=4), overwrite=True)

    # This part to Upload the locally saved JSON file to Azure Blob Storage
    #with open(json_filename, "rb") as data:
        #blob_client.upload_blob(data)

    st.write("Input data has been saved and uploaded successfully to inputdata Azure blob storage.")






























def generate_random_coordinates(left_up, right_down, num_places):
    random_coordinates = []
    
    for _ in range(num_places):
        lat = random.uniform(left_up[0], right_down[0])
        lon = random.uniform(left_up[1], right_down[1])
        random_coordinates.append((lat, lon))
    
    return random_coordinates

def get_address_info(location):
    street = location.raw.get("address", {}).get("road", "")
    city = location.raw.get("address", {}).get("city", "")
    municipality = location.raw.get("address", {}).get("municipality", "")  
    country = location.raw.get("address", {}).get("country", "")
    return f"{street}, {city}, {municipality}, {country}"


# Generate a filename
json_filename = "sim_places.geojson"

# Fetch the Azure Blob Storage connection string from Azure Key Vault using DefaultAzureCredential
vault_url = "https://keyvaultforhamk.vault.azure.net/"
secret_name = "inputdatatoazureblob"  # Replace with the name of your secret
credential = DefaultAzureCredential()
key_vault_secret = SecretClient(vault_url=vault_url, credential=credential).get_secret(secret_name)
# Use the fetched connection string
connection_string = key_vault_secret.value
container_name = "geojsonfiles"
blob_name = json_filename
# Upload the JSON file to Azure Blob Storage
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)




st.sidebar.image("/.streamlit/Smart_research_unit_violet_150.png",use_column_width=True)
generator_choice = st.sidebar.radio("Choose a Generator", ("Random Addresses Generator", "Manually Addresses to Coordinates Converter", "CSV to Coordinates Converter"))


if generator_choice == "Random Addresses Generator":




    st.title("Random Addresses Generator")
    num_places = st.number_input("Enter the number of random places:", min_value=1, value=10, step=1)
    left_up_lat = st.number_input("Enter the latitude of left-up corner:", value=61.0300)
    left_up_lon = st.number_input("Enter the longitude of left-up corner:", value=24.2050)
    right_down_lat = st.number_input("Enter the latitude of right-down corner:", value=60.8300)
    right_down_lon = st.number_input("Enter the longitude of right-down corner:", value=24.7400)

    left_up = (left_up_lat, left_up_lon)
    right_down = (right_down_lat, right_down_lon)







    # Load existing GeoJSON file if it exists
    geojson_filename = "./generated_places.geojson"
    existing_features = []
    if os.path.exists(geojson_filename):
        with open(geojson_filename, "r") as geojson_file:
            existing_data = json.load(geojson_file)
            existing_features = existing_data.get("features", [])



    if st.button("Generate Places"):
        random_coordinates = generate_random_coordinates(left_up, right_down, num_places)
        
        geolocator = Nominatim(user_agent="place_finder")
        
        st.header("Generated Places:")
        new_features = []

        for i, (lat, lon) in enumerate(random_coordinates):
            location = geolocator.reverse((lat, lon), exactly_one=True)
            if location:
                address = get_address_info(location)
                municipality = location.raw.get("address", {}).get("municipality", "")
                
                # Create a new feature for the current location
                new_feature = { "type": "Feature","properties": {"Osoite": address, "Kunta": municipality }, "geometry": { "type": "Point", "coordinates": [lon, lat] }  }
                
                new_features.append(new_feature)

                st.write(f"{i+1}. {address}, {municipality}, {lat}, {lon}")
            else:
                st.write(f"{i+1}. Unknown address (Latitude: {lat}, Longitude: {lon})")

        
        # Prepare the complete GeoJSON data
        updated_geojson_data = { "type": "FeatureCollection","name": "sim_test_sites","crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": new_features }

        # Upload the JSON data to Azure Blob Storage
        blob_client.upload_blob(json.dumps(updated_geojson_data, indent=2), overwrite=True)

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob-sim_places.geojson")





        































def get_coordinates_from_address(address):
    geolocator = Nominatim(user_agent="place_finder")
    location = geolocator.geocode(address)
    if location:
        return location.latitude,location.longitude, location.raw.get("address", {}).get("municipality", "") 
    return None, None, None



if generator_choice == "Manually Addresses to Coordinates Converter":
    st.title("Manually Addresses to Coordinates Converter")
    num_addresses = st.number_input("Enter the number of addresses:", min_value=1, value=1, step=1)

    # Load existing GeoJSON file if it exists
    geojson_filename = "./sim_places.geojson"
    existing_features = []
    if os.path.exists(geojson_filename):
        with open(geojson_filename, "r") as geojson_file:
            existing_data = json.load(geojson_file)
            existing_features = existing_data.get("features", [])

    new_features = []

    for i in range(num_addresses):
        st.write(f"Address {i+1}")
        col1, col2= st.columns(2)
        with col1: input_address = st.text_input(f"Enter address {i+1}:", key=f"address_{i}", placeholder="Example: Hämeentie 23, Hämeenlinna, Finland")
        with col2: input_name = st.text_input(f"Enter name for address {i+1}:", key=f"place_name_{i}")  #this line for names
        
        if input_address:
            lat, lon, municipality = get_coordinates_from_address(input_address)
            if lat is not None and lon is not None:
                address_info = {
                    "place_name": input_name,
                    "address": input_address,
                    "latitude": lat,
                    "longitude": lon,
                    "municipality": municipality,
                }
                st.write(f"{input_name} Coordinates for '{input_address}', ,  {lat}, {lon}" )

            
                new_feature = {
                    "type": "Feature",
                    "properties": {"Osoite": input_address, "Kunta": municipality },
                    "geometry": {"type": "Point", "coordinates": [lon, lat]}
                }

                new_features.append(new_feature)
            else:
                st.write(f"Couldn't find coordinates for '{input_address}'")

    if st.button("Save Addresses to GeoJSON"):
        all_features = existing_features + new_features
        updated_geojson_data = {
            "type": "FeatureCollection",
            "name": "sim_test_sites",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": all_features
        }
        # Upload the JSON data to Azure Blob Storage
        blob_client.upload_blob(json.dumps(updated_geojson_data, indent=2), overwrite=True)

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob-sim_places.geojson")





if generator_choice == "CSV to Coordinates Converter":
    st.title("CSV to GeoJSON Converter")

        # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        # Read the uploaded CSV file into a DataFrame
        df = pd.read_csv(uploaded_file)

        # Get column names for user selection
        column_names = df.columns.tolist()

        # Get user inputs for mapping columns to attributes
        latitude_col = st.selectbox("Select the column that corresponds to latitudes", column_names)
        longitude_col = st.selectbox("Select the column that corresponds to longitudes", column_names)
        name_col = st.selectbox("Select the column that corresponds to municipality", column_names)

        address_option = st.radio("Choose the address format:", ("Single Column", "Multiple Columns"))

        if address_option == "Single Column":
            address_col = st.selectbox("Select the column that corresponds to addresses", column_names)
        else:
            address_cols_input = st.text_input("Enter the column names for address (comma-separated)", placeholder="For example: column1,column2,column3....")  # Provide example inside placeholder
            address_cols = [col.strip() for col in address_cols_input.split(",")]
            address_col = None  # We'll handle this below

        if st.button("Convert to GeoJSON"):
            geojson_features = []

            for index, row in df.iterrows():
                lat = row[latitude_col]
                lon = row[longitude_col]
                name = row[name_col]

                if address_option == "Single Column":
                    address = row[address_col]
                else:
                    # Combine multiple address columns into a single value
                    address_components = [row[col] for col in address_cols]
                    address = ", ".join(filter(None, address_components))

                feature = {
                    "type": "Feature",
                    "properties": {"Osoite": address, "Kunta": name},
                    "geometry": {"type": "Point", "coordinates": [lon, lat]}
                }
                geojson_features.append(feature)

            geojson_data = {
                "type": "FeatureCollection",
                "name": "sim_test_sites",
                "crs": {
                    "type": "name",
                    "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
                },
                "features": geojson_features
            }

            # Upload the JSON data to Azure Blob Storage
            blob_client.upload_blob(json.dumps(geojson_data, indent=2), overwrite=True)

            st.write(f"Data has been saved and uploaded successfully to geojsonfiles Azure blob-sim_places.geojson")
            

