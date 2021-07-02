// make sure start date is before end date i.e.
// if one changes incorrectly, change the other as well
function checkStartDate() {
  const start_input = $("input[name=start_date]")[0];
  const end_input = $("input[name=end_date]")[0];
  if(start_input.valueAsDate > end_input.valueAsDate) {
    start_input.value = end_input.value;
  }
}
function checkEndDate() {
  const start_input = $("input[name=start_date]")[0];
  const end_input = $("input[name=end_date]")[0];
  if(start_input.valueAsDate > end_input.valueAsDate) {
    end_input.value = start_input.value;
  }
}

$(document).ready(
  () => {
    $("input[name=end_date]").blur(checkStartDate);
    $("input[name=start_date]").blur(checkEndDate);
    // blur the focused element in case Enter was used to submit
    $("form#teacher-list-form").submit(() => $(":focus").blur());
  }
);
