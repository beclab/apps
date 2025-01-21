#### Default credentials
Username: admin 
Password: password
Please change username and password as soon as possible.

#### Sync Setup Guide
1. Install Obsidian LiveSync on Olares and Obsidian Client on you computer or cellphone.

2. Install and Enable Sync Plugin on Primary Device
    * Open Obsidian Client, in Vault-> Settings-> Community Plugins-> Turn on Community Plugins-> Browse, install "Self-hosted LiveSync".
    * Enable this plugin at Settings-> Community Plugins

3. Setup Remote Database.
    * Login to Obsidian LiveSync with default credentials, and get the app url (e.g. https://8591294e.YOUR_OLARES_NAME.olares.com) and configure information.
    * Set the configurations at Self-hosted LiveSync-> Remote Database configuration.
    * The database name must consist of lowercase alphabetic characters.

4. Setup the Subsequent Device
    * Install and enable "Self-hosted LiveSync" in the same way as on the primary device.
    * In Self-hosted LiveSync->Setup wizard, use Open setup URI. Paste the setup URI from Primary Device (you can get it by clicking the 'Copy setup URI' button on the same page at primary device)
    * If you enable 'End to End Encryption', use Passphrase instead of URI
    * Choose 'Set it up as secondary or subsequent device'

5. Start Sync 
    * Open realtime live sync on both device at Setting-> Community Plugin-> Self-hosted LiveSync->Sync Setting-> LiveSync
    * Enjoy LiveSync!



