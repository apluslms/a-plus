function participants_list(participants, api_url, is_teacher) {
  participants.sort(function(a, b) { return a.id.localeCompare(b.id); });

  function get_participants() {
    return $('#participants').children();
  }

  if (is_teacher) {
    create_tagging_dropdown =
      get_create_tagging_dropdown_closure({ api_url: api_url });
    get_users_for_user = function (user_id) {
      // If this user's box is not checked, return this user.
      // Else, return all checked users.
      return function () {
        const $user_box = get_participants()
          .find('#students-select-' + user_id);
        if (!$user_box.prop('checked')) {
          return [user_id]
        } else {
          const checked = $.makeArray(get_participants()
            .find('input:checked'));
          return checked.map(function (box) {
            return parseInt(box.getAttribute('value'), 10);
          });
        }
      }
    }
    extra_click_handler = function (data) {
      // Append tag id to participant's tag_ids
      participants
        .find(function (p) { return p.user_id === data.user.id; })
        .tag_slugs.push(data.tag.slug);
    }
  }

  var filterItems = function (participants) {
    const filters = $.makeArray($('.filter-users button:has(.glyphicon-check)'))
      .map(function (elem) {
        return $(elem).attr('data-tagslug');
      });
    return participants.map(function (participant) {
      // Set intercetion tags ∩ filters
      const intersect = participant.tag_slugs.filter(function (tag) {
        return filters.indexOf(tag) >= 0;
      });
      return intersect.length === filters.length;
    });
  };

  $('#participants-number').text(participants.length);
  get_participants().remove();
  participants.forEach(function(participant) {
    const user_id = participant.user_id;
    const tags_id = 'tags-' + user_id;
    const row = $('<tr></tr>')
      .attr({ id: 'participant-' + user_id, 'data-user-id': user_id })
      .appendTo('tbody');
    var link = $('<a></a>').attr('href', participant.link);
    if (is_teacher) {
      $('<td></td>').append(
        $('<input>').attr({
          id: 'students-select-' + user_id,
          type: 'checkbox',
          name: 'students',
          value: user_id,
        })
      ).appendTo(row);
    }
    $('<td></td>')
      .append(link.clone().text(participant.id))
      .addClass('order-id')
      .attr({ 'data-order-by': participant.id })
      .appendTo(row);
    $('<td></td>')
      .append(link.clone().text(participant.last_name))
      .addClass('order-last')
      .attr({ 'data-order-by': participant.last_name })
      .appendTo(row);
    $('<td></td>')
      .append(link.clone().text(participant.first_name))
      .addClass('order-first')
      .attr({ 'data-order-by': participant.first_name })
      .appendTo(row);
    $('<td></td>').append(
      link.clone().text(participant.email || participant.username)
    ).appendTo(row);
    $('<td></td>')
      .addClass('usertags-container')
      .attr({ 'data-user-id': participant.user_id })
      .html(participant.tags)
      .appendTo(row);
  });

  if (is_teacher) {
    // Toggle select all checkbox status automatically
    const $all_box = $('#students-select-all');
    const $individual_boxes = get_participants().find('input:checkbox');

    $all_box.prop('checked', false);

    function set_checkbox_status() {
      const $checked_boxes = $individual_boxes.filter(':checked');
      const at_least_one_checked = $individual_boxes.is(':checked');
      const all_checked = $individual_boxes.length === $checked_boxes.length;
      $all_box.prop('checked', all_checked);
      $all_box.prop('indeterminate', at_least_one_checked && !all_checked);
      $('#selected-number').text($checked_boxes.length);
      return false;
    }

    $individual_boxes.on('change', set_checkbox_status);
    $all_box.on('change', function () {
      $individual_boxes.filter(function (i, elem) {
        return $(elem).parent().parent().is(':not(.hidden)');
      }).prop('checked', $all_box.prop('checked'));
      return set_checkbox_status()
    });

    $(document).on('aplus:translation-ready', function () {
      add_colortag_buttons(
        api_url,
        document.getElementById('participants'),
        participants
      );
    });
  }
  $('a.order-toggle').on('click', function(event) {
    event.preventDefault();

    $('.order-marker').remove();
    $(this).append($('<span class="glyphicon glyphicon-triangle-bottom order-marker" aria-hidden="true"></span>'));
    const order_by_class = '.' + $(this).attr('id');

    const $sortedParticipants = get_participants().sort(function (a, b) {
      const $a = $(a);
      const $b = $(b);
      return $a.children(order_by_class).attr('data-order-by')
               .localeCompare(
                 $b.children(order_by_class).attr('data-order-by')
               );
    });
    get_participants().remove();
    $('#participants').append($sortedParticipants);
  });

  $('.filter-users button').on('click', function(event) {
    event.preventDefault();
    var icon = $(this).find('.glyphicon');
    if (icon.hasClass('glyphicon-unchecked')) {
      icon.removeClass('glyphicon-unchecked').addClass('glyphicon-check');
    } else {
      icon.removeClass('glyphicon-check').addClass('glyphicon-unchecked');
    }
    const show = filterItems(participants);
    participants.forEach(function (participant, i) {
      const $row = $('tr#participant-' + participant.user_id);
      if (show[i]) {
        $row.removeClass('hidden');
      } else {
        $row.addClass('hidden');
      }
    });
  });
}
