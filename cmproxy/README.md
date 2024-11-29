## env Environment Variables
You can edit the env value in Yaml via Control Hub

| Environment Variable | Description | Default Value |
| --- | --- | --- |
| OPENAI_API_BASE_URL | OpenAI API interface address | https://api.openai.com |
| OPENAI_API_KEY | OpenAI API key |  sk-xxxxx |
| OPENAI_API_MODEL |  Default model | gpt-3.5-turbo  |
| MJ_SERVER |  MJ proxy interface address  | [Reference for setup](https://github.com/novicezk/midjourney-proxy) |
| MJ_API_SECRET |  MJ proxy secret | Empty  |
| SUNO_SERVER |  SUNO API interface address  | [Reference for setup](https://github.com/SunoAI-API/Suno-API) |
| SUNO_KEY |  SUNO API key | Empty  |
| AUTH_SECRET_KEY |  Access authorization password | None  |
| API_UPLOADER |  Support upload | Disabled  |
| HIDE_SERVER |  Hide server UI on the front end |    |
| CUSTOM_MODELS |  Custom selectable models | None  |
| TJ_BAIDU_ID |  Baidu Analytics ID | None  |
| TJ_GOOGLE_ID |  Google Analytics ID | None  |
| SYS_NOTIFY |  System notifications, supports HTML | None  |
| DISABLE_GPT4 |  Disable GPT-4 | None  |
| GPT_URL | Custom GPT_URL=/gpts.json  | None or your external link |
| UPLOAD_IMG_SIZE | GPT4V upload image size |  1 |
| SYS_THEME | Default theme `light` or `dark`  | dark |
| MJ_IMG_WSRV | Enable `wsrv` image bed  | None (disabled)  |
| AUTH_SECRET_ERROR_COUNT | Brute force prevention: Number of verification attempts NGINX please set `proxy_set_header X-Forwarded-For $remote_addr`  | None  |
| AUTH_SECRET_ERROR_TIME | Brute force prevention: Wait time in minutes  | None  |
| CLOSE_MD_PREVIEW | Do not close input preview | None  |
| UPLOAD_TYPE | Specify upload method [`R2` R2 upload] [`API` Follow UI front-end relay] [`Container` Local container] [`MyUrl` Custom link]  |  Empty |
| MENU_DISABLE  | Disable menu options: gpts, draws, gallery, music |  Empty |
| VISION_MODEL  | Default recognition model Options: `gpt-4o`, `gpt-4-turb`, `gpt-4-vision-preview`, etc. |  Empty |
| SYSTEM_MESSAGE  | Custom default role message |  Empty |
| CUSTOM_VISION_MODELS  | Custom vision models separated by `,` |  Empty |
