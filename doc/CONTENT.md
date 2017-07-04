A+ remote content
=================

A+ can present course chapters and exercises that integrate page content from
external sources. The content can embed other A+ learning objects from the
course module. "Teacher" creates learning objects in the A+ and configures the
`service_url` for them. On A+ view, the remote URL is requested and content is
embedded in the A+ response to user.

### Head

    <head>
      <script src="ignored.js"></script>
      <script src="support.js" data-aplus></script>
      <link rel="stylesheet" href="support.css" data-aplus>
    </head>

Head tags including attribute `data-aplus` will be injected also in the
final A+ page displaying the chapter.

### Body

    <body>
      <h1>Not embedded</h1>
      <div id="aplus" class="entry-content">
        <p>The content to embed.</p>
      </div>
    </body>

The area embedded in the A+ can be limited using `id="aplus"`,
`id="exercise"`, `id="chapter"` or `class="entry-content"`. By default,
the whole body element is embedded.

### Child exercise

    <div data-aplus-exercise="yes" data-aplus-quiz></div>

Embeds a fully functioning other A+ exercise to the content including student
submission status. The embedded exercise must be a child of the loaded exercise
in the exercise hierarchy.

* `data-aplus-exercise`

    A flag to include a child exercise. Exercises are placed in the child order.

* `data-aplus-quiz`

    If attribute is present the exercise feedback will take the place of
    the exercise instruction. This works for quiz type exercises where
    the feedback includes the student answer and chance to post changes.

* `data-aplus-ajax`

    If attribute is present the chapter will not attach any event listeners
    of its own. The exercise is responsible itself to create new graded
    submissions via ajax. The exercise must ask to update exercise info after
    new submission is created:

        window.postMessage({type: "a-plus-refresh-stats"}, "*");

    The exercise can listen for a bind event that triggers when exercise is
    placed to the chapter DOM. Notice that exercise will not receive document
    ready events normally.

        window.addEventListener("message", function (event) {
            if (event.data.type === "a-plus-bind-exercise") {
                console.log("bind events for #" + event.data.id);
            }
        });
