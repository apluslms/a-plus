const Polyglot = require('node-polyglot')

const defaultLang = 'en'
const lang = $( 'html' ).attr('lang') || defaultLang

// Give a warning if locale is not english. Return the transformed phrase
function onMissingKey(key, opts, locale) {
  if (locale !== defaultLang) {
    console.warn('Missing translation for key: "' + key + '"')
  }
  return Polyglot.transformPhrase(key, opts, locale)
}

const polyglot = new Polyglot({ locale: lang, onMissingKey: onMissingKey })

// Map both the keys and the values of obj using the provided function f
function mapObj(obj, f) {
  return Object.keys(obj).reduce(
    (mapped, key) => {
      mapped[f(key)] = f(obj[key])
      return mapped
    },
    {},
  )
}

// Given a regexp match (from str.replace), generate a polyglot placeholder string
function polyglotPlaceholder(m, p1) {
  // String to use when placeholder doesn't have a name
  // Assume that there is at most one non-named placeholder
  const defaultPlaceholder = '%{0}'
  return p1 ? '%{' + p1 + '}' : defaultPlaceholder
}

// Convert python format string so that it is understood by polyglot.
// For details of the python syntax, see e.g. https://pyformat.info/
function pyInterpolationToPolyglot(str) {
  // An old format string consists of a %, followed by a name in parenthesis,
  // field width, precision, length modifier (ignored by python) and a conversion type.
  // Only the % and the conversion type are mandatory; we only care about the name.
  const oldFormat = /%(?:\(([^)]+)\))?[#0 +-]?(?:\*|\d+)?(?:\.(?:\*|\d+))?[hlL]?[diouxXeEfFgGcrs]/g
  // A standard new format string consists of curly brackets and optionally
  // a name, a conversion flag and/or a format specifier.
  // As above, we only care about the name
  const newFormat = /{([^!:}]*)(?:![rs])?(?::[^}]*)?}/g
  // FOOTGUN ALERT! newFormat must be replaced before oldFormat because
  // polyglot-style placeholders match newFormat, therefore flipping the order
  // would result in old style placeholders being transformed twice
  return str.replace(
    newFormat, polyglotPlaceholder
  ).replace(
    oldFormat, polyglotPlaceholder
  )
}

// Transform translation data from django JSONCatalog format to polyglot format
function djangoToPolyglot(data) {
  if (!data.catalog) {
    return data
  }

  // Django has different plural forms as an object with keys 0, 1 etc; we need
  // them separated by four pipes
  const transformedPlurals = mapObj(data.catalog, val =>
    typeof val === 'object' ? Object.values(val).join(' |||| ') : val
  )

  const transformedInterpolations =
    mapObj(transformedPlurals, pyInterpolationToPolyglot)
  return transformedInterpolations
}

function on_ready() {
  // Load the translation files from the URLs specified in the link tags which
  // have a data-translation attribute and hreflang matching the current language.
  const translationFiles = $( `link[data-translation][hreflang=${lang}]` )
    .map((i, e) => $( e ).attr('href'))

  const readyEvent = 'aplus:translation-ready'
  if (translationFiles.length === 0) {
    $(document).trigger(readyEvent)
  }

  let filesLoaded = 0;
  translationFiles.each((i, path) => {
    $.ajax(path, { dataType: 'json' }).done(
      (data) => {
        polyglot.extend(djangoToPolyglot(data))
        filesLoaded += 1
        if (filesLoaded === translationFiles.length) {
          $(document).trigger(readyEvent)
        }
      }
    )
  })
}

/* double wrap.. first ready will be on top of the stack and will add the second as last */
$(function () {
  $(on_ready);
});

module.exports = polyglot.t.bind(polyglot)
