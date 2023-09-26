import json
import os
import streamlit as st
from geopy.geocoders import Nominatim
import random
import pandas as pd
import requests
from datetime import datetime   #Generate a unique filename for each JSON file, by appending a timestamp to the filename
from azure.storage.blob import BlobServiceClient, BlobPrefix #Access to blobs

from azure.identity import DefaultAzureCredential  # Import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient #Get secrets
from azure.mgmt.compute import ComputeManagementClient #To start/stop VM

import folium
from streamlit_folium import st_folium, folium_static

# Set page title
st.title("Älykkäät Tyhjentaminen App")
# Add instructions for the user
st.write("First, you need to choose in sidebar menu how you want to provide input data:  \n  1)Random Addresses Generator: enter the numbers and area (rectangle) to generate random addresses  \n  2)Manually type the addresses and optionally names for the places  \n  3)Addresses from your CSV: upload your CSV file with location data and select the corresponding column (columns)  \n  Save all files to the Azure and press start")

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


generator_choice = st.sidebar.radio("Choose a Generator of addresses:", ("Random Addresses Generator", "Manually Addresses to Coordinates Converter", "Addresses from your CSV"))

generator_choice_depots = st.sidebar.radio("Choose a Generator of Depot addresses:", ("Random Depot Addresses Generator", "Manually Addresses to Coordinates Converter", "Depot addresses from CSV"))

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
    sim_runtime_days = st.number_input("Simulation runtime (in days)", min_value=1, step=1)
    load_capacity = st.number_input("Load capacity of the truck, Tonnes", min_value=1.0, step=0.1)
    max_route_duration = st.number_input("Max route duration per day, Minutes (9h-break=495min)", min_value=1, step=1) 
    
with col2:
    break_duration = st.number_input("Break duration, Minutes ,Break after 1/2 of drivetime", min_value=1, step=1)
    num_breaks_per_shift = st.number_input("Numbers of brakes per shift", min_value=1, step=1)
    pickup_duration = st.number_input("Pickup duration  time, Minutes", min_value=1, step=1) 

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
json_filename = "sim_test_sites.geojson" #this name will be used in simulation app

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
    left_up_lat = st.number_input("Enter the latitude of left-up corner of rectangle:", value=61.0300)
    left_up_lon = st.number_input("Enter the longitude of left-up corner of rectangle:", value=24.2050)
    right_down_lat = st.number_input("Enter the latitude of right-down corner of rectangle:", value=60.8300)
    right_down_lon = st.number_input("Enter the longitude of right-down corner of rectangle:", value=24.7400)

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





if generator_choice == "Addresses from your CSV":
    st.title("Addresses from your CSV")

        # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], key="uploader1")

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
            address_cols_input = st.text_input("Enter the column names for address (comma-separated)", placeholder="Example: column1,column2,column3...")  # Provide example inside placeholder
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


if generator_choice_depots == "Random Depot Addresses Generator":

    st.title("Random Depot Addresses Generator")
    num_places = st.number_input("Enter the number of random depot places:", min_value=1, max_value=10, value=1, step=1)
    if "left_up_lat" in locals():
        left_up_lat2 = left_up_lat
        left_up_lon2 = left_up_lon
        right_down_lat2 = right_down_lat
        right_down_lon2 = right_down_lon
        left_up = (left_up_lat2, left_up_lon2)
        right_down = (right_down_lat2, right_down_lon2)
    else:
        left_up_lat2 = st.number_input("Enter the latitude of left-up corner of rectangle:", value=61.0300)
        left_up_lon2 = st.number_input("Enter the longitude of left-up corner of rectangle:", value=24.2050)
        right_down_lat2 = st.number_input("Enter the latitude of right-down corner of rectangle:", value=60.8300)
        right_down_lon2 = st.number_input("Enter the longitude of right-down corner of rectangle:", value=24.7400)
    left_up = (left_up_lat2, left_up_lon2)
    right_down = (right_down_lat2, right_down_lon2)
    # Load existing GeoJSON file if it exists
    geojson_filename = "./generated_depot_places.geojson"
    existing_features = []
    if os.path.exists(geojson_filename):
        with open(geojson_filename, "r") as geojson_file:
            existing_data = json.load(geojson_file)
            existing_features = existing_data.get("features", [])



    if st.button("Generate Depot Places"):
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
                new_feature = { "type": "Feature","properties": {"Osoite": address, "Kunta": municipality,"num_vehicles": 1 }, "geometry": { "type": "Point", "coordinates": [lon, lat] }  }
                
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
    num_depots = st.number_input("Enter the number of addresses:", min_value=1, max_value=10, value=1, step=1)

    # Load existing GeoJSON file if it exists
    geojson_filename = "./sim_places.geojson"
    existing_features = []
    if os.path.exists(geojson_filename):
        with open(geojson_filename, "r") as geojson_file:
            existing_data = json.load(geojson_file)
            existing_features = existing_data.get("features", [])

    new_features = []

    for i in range(num_depots):
        st.write(f"Address {i+1}")
        col1, col2, col3 = st.columns(3)
        with col1: input_address = st.text_input(f"Enter address {i+1}:", key=f"depot_address_{i}", placeholder="Hämeentie 23, Hämeenlinna, Finland")
        with col2: input_name = st.text_input(f"Enter name for address {i+1}:", key=f"depot_name_{i}")  #this line for names
        with col3: num_vehicles = st.number_input(f"Number of trucks for address {i+1}:", min_value=1, value=1, step=1)
        if input_address:
            lat, lon, municipality = get_coordinates_from_address(input_address)
            if lat is not None and lon is not None:
                address_info = {
                    "depot_name": input_name,
                    "depot_address": input_address,
                    "latitude": lat,
                    "longitude": lon,
                    "municipality": municipality,
                    "num_vehicles": num_vehicles,  # Assign the number of trucks from user input
                }
                st.write(f"{input_name} Coordinates for '{input_address}', {lat}, {lon}, num_vehicles: {num_vehicles}" )

            
                new_feature = {
                    "type": "Feature",
                    "properties": {"Osoite": input_address, "Kunta": municipality, "num_vehicles": num_vehicles},  #number of trucks from user input 
                    "geometry": {"type": "Point", "coordinates": [lon, lat]}
                }

                new_features.append(new_feature)
            else:
                st.write(f"Couldn't find coordinates for '{input_address}'")

    if st.button("Save Depot Addresses to GeoJSON"):
        all_features = existing_features + new_features
        updated_geojson_data = { "type": "FeatureCollection", "name": "sim_test_terminals", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": all_features  }
        # Upload the JSON data to Azure Blob Storage
        blob_client.upload_blob(json.dumps(updated_geojson_data, indent=2), overwrite=True)

        st.write("Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_terminals.geojson")





if generator_choice_depots == "Depot addresses from CSV":
    st.title("Depot addresses from your CSV")

        # Upload CSV file
    uploaded_file2 = st.file_uploader("Upload a CSV file", type=["csv"], key="uploader2")

    if uploaded_file2 is not None:
        # Read the uploaded CSV file into a DataFrame
        df = pd.read_csv(uploaded_file2)

        # Get column names for user selection
        column_names = df.columns.tolist()

        # Get user inputs for mapping columns to attributes
        latitude_col = st.selectbox("Select the column that corresponds to latitudes", column_names)
        longitude_col = st.selectbox("Select the column that corresponds to longitudes", column_names)
        name_col = st.selectbox("Select the column that corresponds to municipality", column_names)
        number_of_trucks_col = st.selectbox("Select the column that corresponds to number of trucks", column_names)
        address_option = st.radio("Choose the address format:", ("Single Column", "Multiple Columns"))

        if address_option == "Single Column":
            address_col = st.selectbox("Select the column that corresponds to addresses", column_names)
        else:
            address_cols_input = st.text_input("Enter the column names for address (comma-separated)", placeholder="For example: column1,column2,column3....")  # Provide example inside placeholder
            address_cols = [col.strip() for col in address_cols_input.split(",")]
            address_col = None  

        if st.button("Convert to GeoJSON"):
            geojson_features = []

            for index, row in df.iterrows():
                lat = row[latitude_col]
                lon = row[longitude_col]
                name = row[name_col]
                num_vehicles = row[number_of_trucks_col]  # Get number of vehicles from CSV
                if address_option == "Single Column":
                    address = row[address_col]
                else:
                    # Combine multiple address columns into a single value
                    address_components = [row[col] for col in address_cols]
                    address = ", ".join(filter(None, address_components))

                feature = {
                    "type": "Feature",
                    "properties": {"Osoite": address, "Kunta": name, "num_vehicles": num_vehicles},
                    "geometry": {"type": "Point", "coordinates": [lon, lat]}
                }
                geojson_features.append(feature)

            geojson_data = updated_geojson_data = { "type": "FeatureCollection", "name": "sim_test_terminals", "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },"features": geojson_features  }

            # Upload the JSON data to Azure Blob Storage
            blob_client.upload_blob(json.dumps(geojson_data, indent=2), overwrite=True)

            st.write(f"Data has been saved and uploaded successfully to geojsonfiles Azure blob sim_test_terminals.geojson")

#PART START/STOP VM
# Set your Azure subscription ID and resource group name
vault_url = "https://keyvaultforhamk.vault.azure.net/"
secret_name = "subscription"
key_vault_secret = SecretClient(vault_url=vault_url, credential=credential).get_secret(secret_name)
#Use the fetched subscription_id
subscription_id = key_vault_secret.value
resource_group_name = 'data-benchmarking-2'
vm_name = 'optimizer-hamk'

# Create a Streamlit app
st.title("Press start calculations to continue:")
# Create two columns
col1, col2 = st.columns(2)
# Create a button to start the VM
       
if col1.button("Start calculations"):
    try:
        # Create a DefaultAzureCredential
        credential = DefaultAzureCredential()

        # Create a ComputeManagementClient
        compute_client = ComputeManagementClient(credential, subscription_id)

        # Start the virtual machine
        operation_poller = compute_client.virtual_machines.begin_start(resource_group_name, vm_name)
        operation_poller.result()

        st.success(f"Virtual machine '{vm_name}' has been started.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


# Create a button to deallocate the VM
if col2.button("INTERRUPT"):
    try:
        # Create a DefaultAzureCredential
        credential = DefaultAzureCredential()

        # Create a ComputeManagementClient
        compute_client = ComputeManagementClient(credential, subscription_id)

        # Deallocate the virtual machine
        operation_poller = compute_client.virtual_machines.begin_deallocate(resource_group_name, vm_name)
        operation_poller.result()

        st.success(f"Virtual machine '{vm_name}' has been deallocated.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
st.sidebar.write('\n')
st.sidebar.write('\n')



st.sidebar.write("You can see your result about 10 min after all calculations will be made.")
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
st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')
st.sidebar.write('\n')

st.sidebar.write("Häme University of Applied Sciences  \n  (HAMK) / PO Box 230 13101 Hämeenlinna Finland  \n  +3583 6461")

