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
    } catch(e) {
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
      file = new File([""], "filename");
      if (fileList.length > 0) {
        if (fileList[0].size <= 100 * 1024 * 1024) {
          // File size is smaller than the 100MB limit, read it.
          // Larger files are not read to avoid the out-of-memory browser error.
          file = fileList[0];
        } else {
          // For large files, use the file size as the file content
          file = new File([fileList[0].size.toString()], "filename");
        }
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
        try {
          const hash = md5(hashThis);
          openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback);
        } catch(e) {
          // Skip duplicate check if creating the hash fails for some reason
          submitCallback(exercise, "");
        }
      }
    };
    readNextFile();
  } else {
    try {
      const hash = md5(hashThis);
      openDuplicateModalOrSubmit(exercise, hashes, hash, submitCallback);
    } catch(e) {
      // Skip duplicate check if creating the hash fails for some reason
      submitCallback(exercise, "");
    }
  }
};
