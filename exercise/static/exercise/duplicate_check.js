function openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback) {
  const isDuplicate = hashes.includes(hash);
  if (isDuplicate) {
    // Set the number of the existing duplicate submission
    $("#duplicate-submission-modal").find("[data-dup-submission]").text(hashes.reverse().indexOf(hash) + 1);
    // Unbind previous event handlers and bind a new one
    $("#duplicate-submission-modal-button").off('click');
    $("#duplicate-submission-modal-button").click(function() {
      submitCallback(exercise, hash);
    });
    $("#duplicate-submission-modal").modal()
  } else {
    submitCallback(exercise, hash);
  }
};

function duplicateCheck(exercise, form_element, submitCallback) {
  // Retrieve all the hashes of the previous submissions from the HTML
  const hashes = [];
  const datahashElements = exercise.element.find("[data-hash]");
  for (let elem of datahashElements) {
    try {
      hashes.push(elem.dataset["hash"]);
    } catch(error) {
    }
  }

  // Compute a hash for the current submission
  const formData = new FormData(form_element);
  const formProps = Object.fromEntries(formData);
  // Grader language shouldn't affect the hash
  if (formProps.hasOwnProperty('__grader_lang')) {
    delete formProps['__grader_lang'];
  }
  let hashThis = JSON.stringify(formProps, Object.keys(formProps).sort());

  // File contents are not included in formProps, so we read the files separately
  const inputFileElements = form_element.querySelectorAll('input[type=file]');
  if (inputFileElements.length > 0) {
    const reader = new FileReader();
    reader.onerror = function() {
      // Skip duplicate check
      submitCallback(exercise, "");
    };

    let index = 0;
    function readNextFile() {
      const file = inputFileElements[index++].files[0];
      reader.readAsText(file);
    };
    reader.onload = function() {
      // Concatenate file contents with formProps JSON string
      hashThis += reader.result;
      if (index < inputFileElements.length) {
        // More to do, start loading the next file
        readNextFile();
      } else {
        const hash = md5(hashThis);
        openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback);
      }
    };
    readNextFile();
  } else if (exercise.quiz) {
    const hash = md5(hashThis);
    openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback);
  }
};
