$(function() {
	$('table[data-deviations-list] form').on('submit', function(event) {
	event.preventDefault();
	const deleteUrl = this.action;
	const deviationId = $(this).parents('tr').data('deviationId');
	$.ajax(deleteUrl, {
		type: "POST",
	}).done(function () {
		$('table tr[data-deviation-id="' + deviationId + '"]').remove();
		console.info("delete succeeded");
	}).fail(function(xhr, textStatus, errorThrown) {
		if (xhr.status == 404) {
			alert("Deviation object not found.")
			location.reload()
			console.error(errorThrown);
		} else {
			alert("Unexpected error while removing the deviation: " + xhr.status + " " + errorThrown)
			console.error(xhr.status + ' ' + errorThrown);
		}
	});
});
});
