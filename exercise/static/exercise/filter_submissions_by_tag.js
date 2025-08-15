$(document).ready(function() {
	var checked_buttons = []
    $('button.filter-tag').click(function() {
        var tagSlug = $(this).data('tagslug');

        if ($(this).find('i').hasClass('bi-square')) {
            $(this).find('i').removeClass('bi-square').addClass('bi-check-square');
            checked_buttons.push(tagSlug);
            filterSubmissions(checked_buttons)
        } else {
            $(this).find('i').removeClass('bi-check-square').addClass('bi-square');
            var index = checked_buttons.indexOf(tagSlug);
            if (index !== -1) {
                checked_buttons.splice(index, 1);
            }
            filterSubmissions(checked_buttons)
        }
    });

});

function filterSubmissions(checked_buttons) {
	let trs = document.getElementsByTagName('table')[0].getElementsByTagName('tr');

	let submissionTags = [];

	for (let i = 0; i < trs.length; i++) {
		let tagTd = trs[i].getElementsByTagName('td')['submission_tags'];

		if (tagTd) {
			let parser = new DOMParser();
			let doc = parser.parseFromString(tagTd.innerHTML, "text/html");

			let tagSlugs = Array.from(doc.getElementsByTagName('span')).map((el) => el.getAttribute('data-tagslug'));

			submissionTags.push(...tagSlugs);

			let checkedButtonsArr = checked_buttons.map(item => item.replace(/;/g, ""));

			if (checkedButtonsArr.length > 0 && !checkedButtonsArr.every(slug => tagSlugs.includes(slug))) {
				trs[i].style.display = 'none';
			}
			else {
				trs[i].style.display = 'table-row';
			}

		}
	}
};
