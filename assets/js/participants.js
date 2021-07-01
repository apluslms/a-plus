function participants_list(participants, api_url, is_teacher, enrollment_statuses) {
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

  var filter_items = function (participants) {
    const filterTags = $.makeArray($('.filter-users button.filter-tag:has(.glyphicon-check)'))
      .map(function (elem) {
        return $(elem).attr('data-tagslug');
      });
    const filterStatuses = $.makeArray($('.filter-users button.filter-status:has(.glyphicon-check)'))
      .map(function (elem) {
        return $(elem).attr('data-status');
      });
    return participants.map(function (participant) {
      // Set intercetion tags ∩ filters
      const intersectTags = participant.tag_slugs.filter(function (tag) {
        return filterTags.indexOf(tag) >= 0;
      });
      return intersectTags.length === filterTags.length
        && (filterStatuses.length === 0 || filterStatuses.indexOf(participant.enrollment_status) >= 0);
    });
  };

  var remove_participant = function (participant, row, status) {
    $.ajax({
      type: 'DELETE',
      url: api_url + 'students/' + participant.user_id + '/?status=' + status,
    }).done(function () {
      participant.enrollment_status = status;
      row.find('.status-container a').text(enrollment_statuses[status]);
      row.find('.actions-container').empty();
      refresh_filters();
      refresh_numbers();
    });
  };

  var get_row_action = function (label, icon, action) {
    return $('<button></button>')
      .append(
        $('<span></span>')
        .addClass('glyphicon')
        .addClass('glyphicon-' + icon)
        .attr('aria-hidden', true)
      )
      .append(label)
      .addClass('aplus-button--secondary')
      .addClass('aplus-button--xs')
      .on('click', action);
  };

  var refresh_filters = function () {
    const show = filter_items(participants);
    participants.forEach(function (participant, i) {
      const $row = $('tr#participant-' + participant.user_id);
      if (show[i]) {
        $row.removeClass('hidden');
      } else {
        $row.addClass('hidden');
      }
    });
  };

  var refresh_numbers = function () {
    var activeNumber = participants.filter(function (participant) {
      return participant.enrollment_status === 'ACTIVE';
    }).length;
    var inactiveNumber = participants.length - activeNumber;
    $('#active-participants-number').text(activeNumber);
    $('#inactive-participants-number').text(inactiveNumber);
  };

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
      .addClass('status-container')
      .append(
      link.clone().text(enrollment_statuses[participant.enrollment_status])
    ).appendTo(row);
    $('<td></td>')
      .addClass('usertags-container')
      .attr({ 'data-user-id': participant.user_id })
      .html(participant.tags)
      .appendTo(row);
    var actionsColumn = $('<td></td>')
      .addClass('actions-container');
    if (participant.enrollment_status == 'ACTIVE') {
      actionsColumn.append(
        get_row_action('Remove', 'remove', function () {
          remove_participant(participant, row, 'REMOVED');
        })
      ).append(' ').append(
        get_row_action('Ban', 'minus-sign', function () {
          remove_participant(participant, row, 'BANNED');
        })
      );
    }
    actionsColumn.appendTo(row);
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
    // Don't remove the participant nodes before appending them again.
    // It's useless because append() already moves nodes instead of cloning,
    // and removing the nodes causes them to lose their event handlers.
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
    refresh_filters();
  });

  refresh_filters();
  refresh_numbers();
}
