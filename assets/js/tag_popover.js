function add_colortag_buttons(api_url, mutation_target, participants) {
  if (typeof get_users_for_user !== 'function') {
    get_users_for_user = function (user_id) {
      return function () { return [user_id]; };
    };
  }

  // Get popover button dictionaries
  const colortag_buttons = function (elem) {
    const $elem = $(elem);
    const tag_id = parseInt($elem.attr('data-tagid'), 10);
    const user_id = parseInt(
      $elem.parents('[data-user-id]').attr('data-user-id'), 10
    );
    const button_id_prefix = 'participant-' + user_id + '-tag-' + tag_id + '-';
    // Define a 'fake' participants list if it is not defined, to work
    // seamlessly on both the participants list page and other pages
    const participants_ = participants ? participants : [{
      user_id: user_id,
      tag_ids: [tag_id],
    }];

    const filter_button = {
      id: button_id_prefix + 'filter',
      classes: 'btn-default btn-xs',
      text: _('Toggle filtering by tag'),
      onclick: function () {
        $('.filter-users button[data-id="' + tag_id + '"]').trigger('click');
        return false;
      },
    };
    const remove_button = {
      id: button_id_prefix + 'remove',
      classes: 'btn-danger btn-xs',
      text: _('Remove tagging'),
      onclick: function () {
        $.ajax({
          type: 'GET',
          url: api_url + 'taggings/?tag_id=' + tag_id,
          dataType: 'json',
        }).done(function (tagging_data) {
          const taggings = tagging_data.results;
          const user_ids = get_users_for_user(user_id)();
          const remove_taggings = function () {
            user_ids.forEach(function (user_id) {
              const this_tagging = taggings.find(function (tagging) {
                return tagging.user.id === user_id;
              });
              if (!this_tagging) {
                return;
              }

              $.ajax({
                type: 'DELETE',
                url: this_tagging.url,
              }).done(function () {
                $('[data-user-id="' + user_id + '"] ' +
                  '.colortag[data-tagid="' + tag_id +'"]'
                ).remove();
                // Remove tag from tag_ids
                const tag_ids = participants_
                  .find(function (p) { return p.user_id === user_id; })
                  .tag_ids;
                tag_ids.splice(
                  tag_ids.findIndex(function (t) {return t === tag_id}),
                  1
                );
              });
            });
          };
          if (user_ids.length === 1) {
            remove_taggings();
          } else {
            const user_li = participants_.filter(function (p) {
              return user_ids.indexOf(p.user_id) > -1;
            }).map(function (p) {
              return $('<li>' + p.last_name + ' ' + p.first_name +
                ' &lt;' + (p.email || p.username) + '&gt;</li>'
              )
            });
            // Show confirmation modal
            $('#tag-remove-modal-tagging')
              .html($elem.clone().attr('data-tag-removable', 'false'));
            $('#tag-remove-modal-amount').text(user_ids.length);
            $('#tag-remove-modal-users').empty().append(user_li);
            $('#tag-remove-modal-button')
              .off('click')
              .on('click', remove_taggings);
            $('#tag-remove-modal').modal();
          }
        });
        return false;
      },
    };
    const page_has_filters = $('.filter-users').length > 0;
    return page_has_filters ? [filter_button, remove_button] : [remove_button];
  }

  // Observe added tags
  const tag_selector = '.colortag[data-tag-removable!="false"]';
  const mutation_callback = function (mutationsList) {
    mutationsList.forEach(function (mutation) {
      const $added = $(mutation.addedNodes);
      $added.each(function (i, elem) {
        $elem = $(elem);
        if (!$elem.is(tag_selector)) {
          return;
        }
        $elem.buttons_popover(colortag_buttons);
      });
    });
  };
  const observer = new MutationObserver(mutation_callback);
  observer.observe(mutation_target, { childList: true, subtree: true });

  $(tag_selector).buttons_popover(colortag_buttons);
}
