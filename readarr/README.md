### How to add Download Client for Readarr
1. Install a Download Client from the Market
2. Retrieve the API Endpoint of the Download Client
    - Open Control Hub and navigate to CRDs page
    - In 'sys.bytetrade.io' section, locate 'ProviderRegistry' and find the provider information for the Download Client
        - The name is typically in the format legacy-appname.
    - Click on 'Edit YAML', and in the popup window, copy the endpoint URI
        - The URI usually follows the format appname-svc.appname-username:port
3. Add the Download Client in Readarr
    - Open Readarr and go to Settings > Download Clients
    - Choose your download cilent and fill in the setup page
    - Paste the endpoint domain into the Host field and the port number into the Port field. 
        - For example, if using Transmission, it should be:
            - Host: transmission-svc.transmission-yourusername
            - Port: 9091
    - Enter the Username and Password for your Download Client. Leave these fields blank if no authentication is required.
    - Click 'Test' at the bottom. If the test passes, click 'Save' to complete the setup.