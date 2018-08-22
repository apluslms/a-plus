$(function() {
	function json_parse(data) {
		try {
			return JSON.parse(data);
		} catch(e) {
			return null;
		}
	}

	$(".local-storage-fields").each(function() {
		const ul = $(this);
		ul.addClass('list-group');
		const tooltip = ul.data('forget-text');
		const ls = window.localStorage;
		let found = 0;
		for (let i = 0; i < ls.length; i++) {
			const key = ls.key(i);
			const data = json_parse(ls.getItem(key));
			if (key.indexOf("external_service_") != 0 || data === null)
				continue;
			console.log(data);
			const li = $("<li>" + (data.title === undefined ? key : data.title) + "</li>");
			li.addClass('list-group-item');
			const btn = $('<button class="btn btn-xs btn-danger pull-right"><i class="glyphicon glyphicon-remove"></i></button>');
			btn.on('click', function() {
				li.remove();
				ls.removeItem(key);
			});
			btn.tooltip({placement: 'left', title: tooltip});
			li.append(btn);
			ul.append(li);
			found++;
		}
		if (found == 0)
			ul.parent().hide();
	});
});

