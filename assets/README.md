# How to use SASS in development

1. You'll need to download the SASS version of Bootstrap, ready to customise. A Docker container does this in one step. Inside `assets/vendor/bootstrap/`, run `./get.sh`.
2. There's now a `node_modules` directory inside `assets/vendor/bootstrap` containing just Bootstrap 3 in SASS.
3. Next, in `assets/`, run `docker-compose up`. The output includes warnings and errors from your SASS, so if you run this with `-d`, remember to check the `docker-compose logs` if things don't seem to get built.
4. SASS is now running inside a Docker container, and watching for changes in `assets/sass`. Every file change will trigger a rebuild, which takes about a second and writes the changes to the matching location in `assets/css`.
5. When you're done, commit changes that affect: 
  - `assets/sass` - which contains the more readable changes you've made. These are the ones that need reviewing.
  - `assets/css` - which contains the minified CSS and the map files, which allow you to see the SASS inside developer tools.
  - Note that `node_modules` gets ignored by the `.gitignore` file, so no Bootstrap files get committed.