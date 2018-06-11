# Nginx and shibboleth

Here is minimal documentation about running a-plus under nginx with shibboleth (e.g. with HAKA).
This documentation should be extended.

* nginx shib module: https://github.com/nginx-shib/nginx-http-shibboleth

* nginx config: supporting files

    ```
    cd /etc/nginx
    wget https://raw.githubusercontent.com/nginx-shib/nginx-http-shibboleth/master/includes/shib_clear_headers
    wget https://raw.githubusercontent.com/nginx-shib/nginx-http-shibboleth/master/includes/shib_fastcgi_params
    ```

* packages: `apt-get install shibboleth-sp2-common shibboleth-sp2-utils shibboleth-sp2-schemas xmltooling-schemas`

* copy `*.socket` and `*.service` files under `/etc/systemd/system`

* enable sockets `systemctl enable shibauthorizer.socket shibresponder.socket`

* start sockets `systemctl start shibauthorizer.socket shibresponder.socket`
