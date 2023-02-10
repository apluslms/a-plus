A+ LTI 1.3 tool configuration
=============================

## Generating RSA keys

Using A+ as an LTI 1.3 tool requires generating an RSA keypair, with the private key being in pkcs8 format. A valid keypair can be generated with openssl using the following commands:

```
openssl genrsa -out orig.pem 2048
openssl rsa -in orig.pem -pubout -out public.key
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in orig.pem -out private.key
rm orig.pem
```


## Settings in local development

For local development, A+ settings in e.g. `local_settings.py` can be used. Copy-pasteable example in `lti_local_settings.py`. You still need to change the three `client_id` entries there after adding the tool settings in Moodle.

The following changes should be made in Aplus-manual's (or other test course's) docker-compose.yml file.

Under `volumes`, add:
```
  moodledata:
  moodledb:
```

Under `services`, add moodle:
```
  moodle:
    image: apluslms/run-moodle-astra:1.11-3.11
    depends_on:
      - db
      - grader
    environment:
      MOODLE_DOCKER_DBTYPE: pgsql
      MOODLE_DOCKER_DBNAME: moodle
      MOODLE_DOCKER_DBUSER: moodle
      MOODLE_DOCKER_DBPASS: "m@0dl3ing"
      MOODLE_DOCKER_BROWSER: firefox
      MOODLE_DOCKER_WEB_HOST: "moodle"
      MOODLE_DOCKER_WEB_PORT: "8050"
    ports:
      - "8050:8050"
    volumes:
      - moodledata:/var/www/moodledata
      - ./apache-config/000-default.conf:/etc/apache2/sites-enabled/000-default.conf
      - ./apache-config/ports.conf:/etc/apache2/ports.conf
  db:
    image: postgres:12
    environment:
      POSTGRES_USER: moodle
      POSTGRES_PASSWORD: "m@0dl3ing"
      POSTGRES_DB: moodle
    volumes:
      - moodledb:/var/lib/postgresql/data
```
Create the `local_settings.py` file in the a-plus repo under the `aplus` directory next to the `settings.py` file.
Copy-paste settings from `doc/lti_local_settings.py` and modify them if necessary.
In docker-compose.yml, add the following line in `services.plus.environment`:
```
APLUS_LOCAL_SETTINGS: '/srv/aplus/aplus/local_settings.py'
```
For development, your local a-plus code should be mounted in as well in `services.plus.volumes`:
```
  [your-aplus-code-path]:/srv/aplus/
```

The config mounts files `000-default.conf` and `ports.conf`. The contents of those should be as follows:

`000-default.conf`:
```
<VirtualHost *:8050>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html
        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```
`ports.conf`:
```
Listen 8050
```

Additionally, the development machine's `/etc/hosts` file should include a line like following (acos optional):
```
127.0.0.1 plus moodle acos
```

To add the tool in Moodle, set the following settings when adding a pre-configured external tool:

| Setting                                      | Value                                                          |
|----------------------------------------------|----------------------------------------------------------------|
| **Tool Settings**                            |                                                                |
| Tool URL                                     | http://plus:8000                                               |
| LTI version                                  | LTI 1.3                                                        |
| Public key type                              | RSA key                                                        |
| Public key                                   | your generated public key                                      |
| Initiate login URL                           | http://plus:8000/lti/login/                                    |
| Redirection URI(s)                           | http://plus:8000/lti/login/ <br/> http://plus:8000/lti/launch/ |
| Supports Deep Linking (Content-Item Message) | checked                                                        |
| Content Selection URL                        | http://plus:8000/lti/launch/                                   |
| **Services**                                 |                                                                |
| IMS LTI Assignment and Grade Services        | Use this service for grade sync and column management          |
| **Privacy**                                  |                                                                |
| Share launcher's name with tool              | Always                                                         |
| Share launcher's email with tool             | Always                                                         |

## Settings in production

In production, the relevant settings are set via Django's admin panel, under `PyLTI 1.3 Tool Config`.
