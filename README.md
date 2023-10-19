https://logistic-hamk.azurewebsites.net/
# simulator_input
Streamlit inputs for logistic simulator

Streamlit application for generating and managing place and depot addresses and conducting calculations related to route optimization. 

Generate Addresses:
The application allows you to generate depot addresses in three different ways:
1) Random Addresses Generator:
Select this option to generate random depot places within a specified geographical area.
Specify the number of random depot places you want.
Define the geographical area by providing the latitude and longitude of the left-up and right-down corners of a rectangle.
Click the "Generate Places" button to generate the addresses and view them on the map.
The generated data will be saved to an Azure Blob Storage container.
2) Manually Addresses to Coordinates Converter:
Select this option to manually input depot addresses.
Specify the number of addresses you want to input.
For each address, enter the address, a name, and the number of vehicles at that depot.
Click the "Save Depot Addresses to GeoJSON" button to save the addresses.
Depot Addresses from CSV:
Select this option to import depot addresses from a CSV file.
Upload a CSV file that contains address information, and the application will convert it into depot addresses.
You can specify whether you want more than one vehicle for each depot.
Start Simulation Virtual Machine:

The application provides buttons to start and interrupt a virtual machine.
Starting the virtual machine will initiate route optimization calculations.
Deallocating the virtual machine can be used to interrupt the calculations.

View Results on the Map:

After the calculations are completed, you can view the results on the map.
Click the "Show the result on the map" button to display possible routes to depot places on the map.
The routes are color-coded to represent different vehicles.
View Calculated Files:

You can view files related to the calculations from Azure Blob Storage.
Select a file from the dropdown list.
Additional Information:

The application uses Azure Blob Storage and Azure Key Vault to store and retrieve data.
It's specifically designed for use with route optimization calculations.
