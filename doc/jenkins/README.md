Jenkins is not currently used but the instructions and configurations are left here in case it will be used in the future. Note that the configurations want a `selenium_test_report.xml` file from the selenium tests but it is not produced anymore.

Jenkins setup
=============

1. Installation on Ubuntu

        sudo apt-get install apache2 jenkins jenkins-cli
        echo JAVA_ARGS=\"\$JAVA_ARGS -Dhudson.diyChunking=false\" >> /etc/default/jenkins
        sudo cp etc-apache2-sites-available-plustest /etc/apache2/sites-available/plustest
        sudo a2ensite plustest

2. Install Jenkins plugins

  * Cobertura Plugin
  * Embeddable Build Status Plugin
  * Environment Injector Plugin
  * Git client plugin
  * Git plugin
  * GitHub API Plugin
  * GitHub plugin
  * GitHub Pull Request Builder
  * Xvfb plugin

  Configure GitHub API username.

3. Create Jenkins jobs

        wget http://localhost:8080/jnlpJars/jenkins-cli.jar
        java -jar jenkins-cli.jar -s http://localhost:8080 create-job A-plus-test-PR --username nnn --password ppp < A-plus-test-PR.xml
        java -jar jenkins-cli.jar -s http://localhost:8080 create-job A-plus-test-MASTER --username nnn --password ppp < A-plus-test-MASTER.xml
        java -jar jenkins-cli.jar -s http://localhost:8080 create-job A-plustest-publish --username nnn --password ppp < A-plustest-publish.xml

4. Create virtual environment for A+

  See the deployment document for software requirement details.

        sudo su mkdir /var/aplusenv
        sudo chown jenkins:jenkins /var/aplusenv
        sudo su jenkins
        cd /var/aplusenv
        virtualenv -p python3 .

5. Configure database

  See the deployment document for database creation.

        sudo cp test_local_settings.py /var/lib/jenkins/workspace/A-plustest-publish/local_settings.py
