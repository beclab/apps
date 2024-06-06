### How to Set Up Your Server

After installing the Mastodon application from the Market, you need to configure it to run your private Mastodon server instance.

> **Prerequisites**<br>
> You need an SMTP mail service to provide registration and notification services via email to the users on your server instance.

#### Configuring the Instance Backend

1.  Set up SMTP service
    
    Open Control Hub, in Mastodon-> Configmaps, find the `mastodon-default`, and click Edit YAML to configure SMTP service information.
    ```yaml
    - name: SMTP_SERVER
      value: your_server_address
    - name: SMTP_PORT
      value: 465
    - name: SMTP_PASSWORD
      value: your_password
    - name: SMTP_FROM_ADDRESS
      value: service@example.com
    - name: SMTP_DOMAIN
      value: your.domain
    - name: SMTP_TLStrue
      value: true
    - name: SMTP_DELIVERY_METHOD
      value: smtp
    - name: SMTP_LOGIN
      value: your_token
    ```

2.  Restart the Mastodon service.

    Open Settings and locate Mastodon in the Application Section. Click 'Suspend'. Once the suspension is successful, click 'Resume' to restart Mastodon.

3.  Create an administrator account

    Open the Control Hub, in Mastodon-> Deployments, locate the `mastodon-streaming` and click on 'Pod'. Find a container named `mastodon`, and click the Terminal button.

    Enter the following command in the Terminal to create an admin account and retrieve the initial password.
    ```bash
    tootctl accounts create **NICKNAME** --email **EXMAPLE_EMAILADDRESS** --approve --confirmed --role Owner
    ```

    > **Note**<br>
    > Setting up the account takes approximately 30 seconds. During this time, please stay on this page and refrain from performing any other operations. You will receive the account password once everything is ready.

#### Configuring the Server

1.  Log into the admin account 

    Open the Mastodon application and log in using the administrator email and password that you created in the previous step.

2.  Server Settings

    You can adjust various settings of your Mastodon instance via the Homepage-> Preferences->Administration ->Server Settings.

    For instance, you can differentiate your server from others by giving it a unique name, description, appearance, and other branding elements.

    Additionally, you might want to modify the registration policy, which is 'invite only' by default.

#### Exploring Your Mastodon

1.  Invite users to register

    By default, only users invited by the administrator can join the server. To invite others, go to Preferences -> Invite People to generate an invitation link. New users can then register on this Mastodon Server by visiting the address provided in the invitation link.

2. Follow users

    You can follow users regardless of whether they're registered on your server instance or another server. To find people, search for the User Address. The User Address can either be in the format `@USER_NAME@SERVER_NAME` or `https://SERVER_NAME/@USER_NAME`.

    > **Note**<br>
    > The USER_NAME is not the same as the Display Name. It is an unmodifiable field that is filled in at the time of registration.

    > **Note**<br>
    > For users outside of your instance, you can only see their posts, or 'toots', in the Explore or Feeds stream from the time you start following them. To view all toots, you'll need to visit the user's homepage.

