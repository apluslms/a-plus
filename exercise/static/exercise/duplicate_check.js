function openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback) {
  const isDuplicate = hashes.includes(hash);
  if (isDuplicate && !exercise.disable_duplicate_check) {
    // Set the number of the existing duplicate submission
    $("#duplicate-submission-modal").find("[data-dup-submission]").text(hashes.reverse().indexOf(hash) + 1);
    // Unbind previous event handlers and bind a new one
    $("#duplicate-submission-modal-button").off('click');
    $("#duplicate-submission-modal-button").click(function() {
      $("#duplicate-submission-modal").modal('hide');
      submitCallback(exercise, hash);
    });
    $("#duplicate-submission-modal").modal('show');
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
  const formAsArray = $(form_element).serializeArray();
  // Grader language shouldn't affect the hash
  const formAsArray2 = formAsArray.filter(function(f) { return f.name !== '__grader_lang'; });
  let hashThis = JSON.stringify(formAsArray2);

  // File contents are not included in the JSON string, so we read the files separately
  const inputFileElements = form_element.querySelectorAll('input[type=file]');
  if (inputFileElements.length > 0) {
    const reader = new FileReader();
    reader.onerror = function() {
      // Skip duplicate check
      submitCallback(exercise, "");
    };

    let index = 0;
    function readNextFile() {
      let file;
      const fileList = inputFileElements[index++].files;
      if (fileList.length > 0) {
        file = fileList[0];
      } else {
        file = new File([""], "filename");
      }
      reader.readAsText(file);
    };
    reader.onload = function() {
      // Concatenate file contents with the JSON string
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
  } else {
    const hash = md5(hashThis);
    openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback);
  }
};
