# Notes about using the Moodle frontend (Astra plugin) with the mooc-grader

Astra behaves mostly in the same way as A+, however, there are some differences.

## Moodle activities and course sections

Astra represents one exercise round as one activity module in Moodle.
Forums and assignments are examples of well-known Moodle activities.
Activities are listed in the Moodle course page. Each activity belongs to
a section (numbered 0...N) in the course.

Automatic setup of the course is accessed via the links in the "Astra exercises setup"
block (the block needs to added to the Moodle course first).
Astra supports importing the course configuration from the mooc-grader like A+.
The teacher defines the Moodle section which new Astra activities are inserted into.

## Differences in course or learning object configurations (see [courses/README.md](../courses/README.md))

* `use_wide_column` learning object setting is not (yet) supported in Astra
* `min_group_size` and `max_group_size`: Astra does not (yet) support group submissions
* Astra recognizes an additional setting `submission_file_max_size` for exercises
* `assistants`: Astra tries to find Moodle users with an `idnumber` matching the
  values in the `assistants` list. The users are then enrolled to the Moodle course
  as non-editing teachers. They gain non-editing teacher privileges in the course
  and in the Astra activities (exercise rounds) that have an exercise with
  `allow_assistant_grading` or `allow_assistant_viewing` enabled. The activity-specific
  privileges are basically meaningless while the user has course-wide privileges.
  If this feature behaves badly, for example, because a Moodle site has overwritten
  the default Moodle user roles and given them new names and semantics,
  the `assistants` list should be empty/disabled in the mooc-grader configuration.

## Mathematical notations in course content

Astra supports mathematical notations by forwarding the rendering to the Moodle core.
If the Moodle site and the Moodle coursespace have enabled filters for rendering
mathematics, Moodle finds and renders mathematical notations in the page.
Moodle has multiple methods for rendering mathematics; one of them is based on
the MathJax JavaScript library. The mathematical notations must be surrounded
by correct delimiters: which delimiters are recognized depends on the Moodle
site configuration. If the rendering of mathematics is enabled in Moodle, the
content from the exercise service should not include its own version of, e.g.,
the MathJax library (in a `<script>` element within the exercise HTML content).

By default, the Moodle MathJax filter recognizes two sets of delimiters:
inline formulas use `\( equation \)` and centered formulas use `$$ equation $$`.
For example:
```
<p>
  Variable \(x\) behaves nicely when \( x \rightarrow y \). On the other hand,
  a polynomial equation like $$ x^2 + x + 1 = 0 $$ is too hard to crack for
  some students.
</p>
```

## JavaScript and AJAX in learning objects

Using JavaScript in learning objects (exercise descriptions and chapters) requires
caution in order to make it work correctly. Moodle packages client-side JS code in
AMD modules (Asynchronous Module Definition), however, the AMD libraries and
APIs are not available until they have been loaded in the page. Moodle includes
the libraries at the end of the page, after the content from the exercise service.
If JS code in the learning object waits until the page has loaded, the Moodle AMD
APIs become available and may be loaded for use. Moodle bundles jQuery JS library
as an AMD module: jQuery should be used by loading the AMD module instead of
loading it with a `<script src="jquery URL">` element.

If the learning object HTML content includes inline JS code (code directly inside
`<script>` elements), the script element may use an attribute `data-astra-jquery`
so that Astra automatically wraps the JS code in a `require` call that enables jQuery.
The JS code is embedded at the end of the page so that the AMD APIs are available.
The data attribute may be given a value, which is used as the name for the jQuery
module; '$' is used by default.

```
<script data-astra-jquery>
    $('#exercise').after('<p>jQuery active</p>');
</script>

<script data-astra-jquery="jq">
    jq('#exercise').prepend('<p>jQuery active</p>');
</script>
```

JavaScript code that is included from a separate file (`src` attribute on
`<script>` elements) must call `require` itself to enable jQuery. The `require`
function is available once the page has been loaded.

```javascript
document.addEventListener("DOMContentLoaded", function(event) {
    /* require call that works with Moodle AMD JS API and
       enables the version of jQuery that is bundled with Moodle
    */
    require(["jquery"], function($) {
        // insert your JS code here
        $('#exercise').after('<p>jQuery active</p>');
    });
});
```

JavaScript code in the learning object may also define new AMD modules and
use them with require.

```javascript
document.addEventListener("DOMContentLoaded", function(loadevent) {
    // define a new module that uses jQuery
    define('moocgrader/mymodule', ["jquery"], function($) {
        return {
            myprint: function() {
                $('#exercise').prepend('<p>jQuery active in a new AMD module function</p>');
            },
        };
    });

    // use the new module
    require(['moocgrader/mymodule'], function(mymodule) {
        mymodule.myprint();
    });
});
```


## Bootstrap frontend framework

A+ and MOOC grader templates use the Bootstrap 3 framework. Moodle core includes
a base theme `bootstrapbase` that uses the deprecated Bootstrap version 2.
Astra uses the Bootstrap version from the `bootstrapbase` theme. In addition,
Astra includes selected parts of the Bootstrap 3 CSS rules. The result is that
most of the important Bootstrap 3 components work in Astra, e.g., tooltips, modals,
and dropdowns. Exercise services should use Bootstrap 3 normally in their course
contents and see if it works in Astra (if not, you may need to simplify the content
so that it uses only working components).

Different Moodle sites may have different themes. Other themes may have a different
version of Bootstrap or no Bootstrap at all. Moodle 3.2 includes a new theme called
Boost that is based on Bootstrap 4.

