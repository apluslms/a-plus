
function filterBySubmitter(submitterLabel) {
  const params = new URLSearchParams(window.location.search);
  const submitterName = params.get("submitter");
  if (!submitterName) return;

  const table = $(".filtered-table");
  if (!table.length) return;

  // Find the submitter column index (case-insensitive)
  let submitterIndex = -1;
  table.find("thead > tr:first-child > th").each(function (index) {
    const text = $(this).text().trim().toUpperCase();
    if (text === submitterLabel) {
      submitterIndex = index;
    }
  });

  if (submitterIndex === -1) return;

  // Fill the input in the second row (filter row)
  const filterInput = table.find(`thead > tr:eq(1) > td:eq(${submitterIndex}) input`);
  if (filterInput.length) {
    filterInput.val(submitterName).trigger("keyup");
  }
}
