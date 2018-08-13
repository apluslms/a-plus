Polyglot translation for A+
===========================

Utility tool for flexible loading of JSON translation files into polyglot.
Exports `polyglot.t` as `_` (edit the build command in `package.json` to change).

Requirements
------------

You will need node.js and npm installed to build. Other dependencies will be
installed by npm.

JQuery is required to run the script in browser.

How to use
----------

Install dependencies if you haven't done so already

```
npm install --no-save
```

Build the bundle, which will be put to A+'s `assets/js` folder, and run
collectstatic (if not serving static files from `runserver`). You will need to
repeat this step every time you change `main.js`.

```
npm run build
python ../../manage.py collectstatic
```

In the HTML file, include JQuery and `translate.js`

```
<script src="path/to/jquery.min.js"></script>
<script src="{% static 'js/translate.min.js' %}"></script>
```

Include your translation files in link tags in HTML. The translation files may
be either in [polyglot's](http://airbnb.io/polyglot.js/) native format or in 
[Django JSONCatalog](https://docs.djangoproject.com/en/2.0/topics/i18n/translation/#the-jsoncatalog-view)
format.

```
<link data-aplus="yes" data-translation rel="preload" as="fetch" hreflang="fi" href="foo.fi.json">
etc.
```

The HTML must also have a valid lang attribute, e.g.
```
<html lang="fi">
```

Use the translations in JavaScript, e.g.
```
console.log(_('To %{be} or not to %{be}, that is the %{question}', { be: 'syödä', question: 'pulma' }))
> "syödäkö vai eikö syödä, kas siinäpä pulma"
```

### Customising the Build Process

The bundle is built using `browserify` with `babelify`, and minified using `uglify-js`.
The minified source is put into `assets/js/translate.min.js` and the source mapping
into `assets/js/translate.min.js.map`. If you want to call `polyglot.t` with a
name different than the default `_`, modify the `-s` parameter of `browserify`
in `package.json`.

The source map is automatically modified using `sed` to have the correct URL
of the original JS file. This is somewhat ugly but I couldn't find a combination
of parameters that would automatically insert the correct one.
