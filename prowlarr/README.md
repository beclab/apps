### How to Connect Prowlarr to Sonarr/Radarr/Readarr/Lidarr
1. Install the *arr app from the Market
2. Add Indexer in Prowlarr
    - Navigate to"Indexers > Add Indexer"
    - Add your desired sites to indexer collection. 
3. Sync indexers with *arr app
    - navigate to "Settings > Apps" in Prowlarr, and click the card with big "+" button under "Applications", then select the *arr app accrodingly.
    - Fill in the endpoint url for Prowlarr and *arr Server
        - The format is usually "http://{appname}-svc.{appname}-{your_olares_name}:{service_port}" 
        - For example, the Prowlarr Server url is "http://prowlarr-svc.prowlarr-{your_olares_name}:9696"
        - To find the exact endpoint url of an app, you can open ControlHub and navigate to "CRDs > sys.bytetrade.io > ProviderRegistry". Locate the record named "legacy-{appname}", then click on "Edit Yaml". The endpoint url is in the "spec > endpoint" field.
    - Copy the API key of the *arr app, which can be found in the "Settings > General"
    - Leave the rest as it is. Test if everything is working correctly with the button at the bottom before saving it.
4. Click on "Sync App Indexers", and wait for the process to complete
5. To verify the setup, open the *arr app and go to "Settings > Indexers". You should see the indexers from Prowlarr successfully synced.

### How to add Download Client for Prowlarr

> Please Note: download clients are for Prowlarr in-app searches only and do not sync to apps. You do not need to add them here unless you intend to do searches directly within Prowlarr

1. Install a Download Client from the Market
2. Retrieve the API Endpoint of the Download Client
    - Open Control Hub and navigate to "CRDs" page
    - In "sys.bytetrade.io" section, locate "ProviderRegistry" and find the provider information for the Download Client
        - The name is typically in the format "legacy-appname".
    - Click on "Edit YAML", and in the popup window, copy the endpoint URI
        - The URI usually follows the format "appname-svc.appname-username:port"
3. Add the Download Client in Prowlarr
    - Open Prowlarr and go to "Settings > Download" Clients
    - Choose your download cilent and fill in the setup page
    - Paste the endpoint domain into the Host field and the port number into the Port field. 
        - For example, if using Transmission, it should be:
            - Host: transmission-svc.transmission-yourusername
            - Port: 9091
    - Enter the Username and Password for your Download Client. Leave these fields blank if no authentication is required.
    - Click "Test" at the bottom. If the test passes, click "Save" to complete the setup.    