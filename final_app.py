import json
import os
import streamlit as st
from geopy.geocoders import Nominatim
import random
import pandas as pd
import requests
from datetime import datetime   #generate a unique filename for each JSON file, by appending a timestamp to the filename
from azure.storage.blob import BlobServiceClient, BlobPrefix
from azure.identity import DefaultAzureCredential  # Import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


import folium
from streamlit_folium import st_folium, folium_static



# Set page title
st.title("Älykkäät Tyhjentaminen App")
# Add instructions for the user
st.write("First, you need to choose in sidebar menu how you want to provide input data:  \n  Random Addresses Generator: enter the numbers and area to generate random coordinates  \n  Manually type the addresses and optionally names for the places  \n  CSV to Coordinates Converter: upload a your CSV file with location data and select the corresponding column  \n  Then enter input data for simulation and save both files to the Azure")


st.sidebar.image(".streamlit/Smart_research_unit_violet_150.png",use_column_width=True)




















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






generator_choice = st.sidebar.radio("Choose a Generator of addresses:", ("Random Addresses Generator", "Manually Addresses to Coordinates Converter", "CSV to Coordinates Converter"))

generator_choice_depots = st.sidebar.radio("Depot addresses:", ("Random depot Addresses Generator", "Manually Addresses to Coordinates Converter", "Depot addresses from CSV"))

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
    





# Generate a filename
json_filename = "sim_test_sites.geojson"

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

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_sites.geojson")







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
    geojson_filename = "./sim_and_places.geojson"
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

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_sites.geojson")





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

            st.write(f"Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_sites.geojson")
        




































#TERMINALS PART
# Generate a filename
json_filename = "sim_test_terminals.geojson"

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


if generator_choice_depots == "Random depot Addresses Generator":

    st.title("Random depot Addresses Generator")
    num_places = st.number_input("Enter the number of random depot places:", min_value=1, value=1, step=1)
    if "left_up_lat" in locals():
        left_up_lat2 = left_up_lat
        left_up_lon2 = left_up_lon
        right_down_lat2 = right_down_lat
        right_down_lon2 = right_down_lon
        left_up = (left_up_lat2, left_up_lon2)
        right_down = (right_down_lat2, right_down_lon2)
    else:
        left_up_lat2 = st.number_input("Enter the latitude of left-up corner:", value=61.0300)
        left_up_lon2 = st.number_input("Enter the longitude of left-up corner:", value=24.2050)
        right_down_lat2 = st.number_input("Enter the latitude of right-down corner:", value=60.8300)
        right_down_lon2 = st.number_input("Enter the longitude of right-down corner:", value=24.7400)
    left_up = (left_up_lat2, left_up_lon2)
    right_down = (right_down_lat2, right_down_lon2)
    # Load existing GeoJSON file if it exists
    geojson_filename = "./generated_depot_places.geojson"
    existing_features = []
    if os.path.exists(geojson_filename):
        with open(geojson_filename, "r") as geojson_file:
            existing_data = json.load(geojson_file)
            existing_features = existing_data.get("features", [])



    if st.button("Generate depot Places"):
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
                new_feature = { "type": "Feature","properties": {"Osoite": address, "Kunta": municipality,"NumTrucks": 1 }, "geometry": { "type": "Point", "coordinates": [lon, lat] }  }
                
                new_features.append(new_feature)

                st.write(f"{i+1}. {address}, {municipality}, {lat}, {lon}, NumTrucks: 1")
            else:
                st.write(f"{i+1}. Unknown address (Latitude: {lat}, Longitude: {lon})")

        
        # Prepare the complete GeoJSON data
        updated_geojson_data = { "type": "FeatureCollection", "name": "sim_test_terminals", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": new_features }

        # Upload the JSON data to Azure Blob Storage
        blob_client.upload_blob(json.dumps(updated_geojson_data, indent=2), overwrite=True)

        st.write("Data has been saved and uploaded successfully to  Azure blob sim_test_terminals.geojson")







def get_coordinates_from_address(address):
    geolocator = Nominatim(user_agent="place_finder")
    location = geolocator.geocode(address)
    if location:
        return location.latitude,location.longitude, location.raw.get("address", {}).get("municipality", "") 
    return None, None, None



if generator_choice_depots == "Manually Addresses to Coordinates Converter":
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
        col1, col2, col3 = st.columns(3)
        with col1: input_address = st.text_input(f"Enter address {i+1}:", key=f"address_{i}", placeholder="Example: Hämeentie 23, Hämeenlinna, Finland")
        with col2: input_name = st.text_input(f"Enter name for address {i+1}:", key=f"place_name_{i}")  #this line for names
        with col3: input_number_of_trucks = st.number_input(f"Enter the number of trucks for address {i+1}:", min_value=1, value=1, step=1)
        if input_address:
            lat, lon, municipality = get_coordinates_from_address(input_address)
            if lat is not None and lon is not None:
                address_info = {
                    "place_name": input_name,
                    "address": input_address,
                    "latitude": lat,
                    "longitude": lon,
                    "municipality": municipality,
                    "num_trucks": input_number_of_trucks,  # Assign the number of trucks from user input
                }
                st.write(f"{input_name} Coordinates for '{input_address}', {lat}, {lon}, Number of Trucks: {input_number_of_trucks}" )

            
                new_feature = {
                    "type": "Feature",
                    "properties": {"Osoite": input_address, "Kunta": municipality, "NumTrucks": input_number_of_trucks},  #number of trucks from user input 
                    "geometry": {"type": "Point", "coordinates": [lon, lat]}
                }

                new_features.append(new_feature)
            else:
                st.write(f"Couldn't find coordinates for '{input_address}'")

    if st.button("Save Addresses to GeoJSON"):
        all_features = existing_features + new_features
        updated_geojson_data = { "type": "FeatureCollection", "name": "sim_test_terminals", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": all_features  }
        # Upload the JSON data to Azure Blob Storage
        blob_client.upload_blob(json.dumps(updated_geojson_data, indent=2), overwrite=True)

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_terminals.geojson")





if generator_choice_depots == "Depot addresses from CSV":
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

            geojson_data = updated_geojson_data = { "type": "FeatureCollection", "name": "sim_test_terminals", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": geojson_features  }

            # Upload the JSON data to Azure Blob Storage
            blob_client.upload_blob(json.dumps(geojson_data, indent=2), overwrite=True)

            st.write(f"Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_terminals.geojson")




st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write("You can see your result about 10 min after all calculation will be made.")
if st.sidebar.button("Show the result on the map"):
    
    # Your connection string and container name
    vault_url = "https://keyvaultforhamk.vault.azure.net/"
    secret_name = "inputdatatoazureblob"  # Replace with the name of your secret
    credential = DefaultAzureCredential()
    key_vault_secret = SecretClient(vault_url=vault_url, credential=credential).get_secret(secret_name)

# Use the fetched connection string
    connection_string = key_vault_secret.value
    container_name = "output"
    # List all blobs in the container
    blobs = blob_service_client.get_container_client(container_name).list_blobs()
    blob_prefix = "/app/log/routes_log_"  # The common part of the blob name

    # Initialize the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # List all blobs in the container with the specified prefix
    blobs = blob_service_client.get_container_client(container_name).list_blobs(name_starts_with=blob_prefix)

    # Initialize variables to keep track of the latest blob and its timestamp
    latest_blob = None
    latest_timestamp = None

    # Iterate through the blobs to find the latest one
    for blob in blobs:
        if blob.name.endswith(".csv"):
            if latest_blob is None or blob['last_modified'] > latest_timestamp:
                latest_blob = blob
                latest_timestamp = blob['last_modified']
    

    # Check if a latest blob was found
    if latest_blob:
        latest_blob_name = latest_blob['name']
        st.write('\n')
        st.write('\n')
        st.write('\n')
        st.write(f"Latest blob in the container: {latest_blob_name}")

        # Download the latest blob and process it (replace with your code)
        with open("latest_blob.csv", "wb") as f:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=latest_blob_name)
            blob_data = blob_client.download_blob()
            f.write(blob_data.readall())

        st.header("Possible routes to the places on the map:")


        data = pd.read_csv("latest_blob.csv")

        # Create a base map
        center_coords = (data['y'].mean(), data['x'].mean())
        m = folium.Map(location=center_coords, zoom_start=8)

        # Group data by 'v' (vehicle) column
        grouped = data.groupby('v')

        # Define colors for each vehicle
        colors = {0: 'blue', 1: 'red'}

        # Iterate through groups and create polylines
        for vehicle, group in grouped:
            coordinates = list(zip(group['y'], group['x']))  # Swap 'x' and 'y' to match latitude and longitude
            color = colors.get(vehicle, 'black')  # Default color is black if not defined
            folium.PolyLine(locations=coordinates, color=color).add_to(m)
        #st_data = st_folium(m, width=700)
        folium_static(m)
        
    else:
        st.write("No blobs found in the container with the specified prefix.")
    


# st.sidebar.write('\n')
# st.sidebar.write('\n')
# st.sidebar.write('\n')
# st.sidebar.write('\n')
# st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')


st.sidebar.write("Häme University of Applied Sciences  \n  (HAMK) / PO Box 230 13101 Hämeenlinna Finland  \n  +3583 6461")
