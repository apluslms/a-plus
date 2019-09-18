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
    const tag_slug = $elem.attr('data-tagslug');
    const user_id = parseInt(
      $elem.parents('[data-user-id]').attr('data-user-id'), 10
    );
    const button_id_prefix = 'participant-' + user_id + '-tag-' + tag_id + '-';
    // Define a 'fake' participants list if it is not defined, to work
    // seamlessly on both the participants list page and other pages
    const participants_ = participants ? participants : [{
      user_id: user_id,
      tag_slugs: [tag_slug],
    }];

    const filter_button = {
      id: button_id_prefix + 'filter',
      classes: 'btn-default btn-xs',
      text: _('Toggle filtering by tag'),
      onclick: function () {
        $('.filter-users button[data-tagslug="' + tag_slug + '"]').trigger('click');
        return false;
      },
    };
    const remove_button = {
      id: button_id_prefix + 'remove',
      classes: 'btn-danger btn-xs',
      text: _('Remove tagging'),
      onclick: function () {
        const user_ids = get_users_for_user(user_id)();
        // Split the user ids into chunks of ten ids.
        const split_uids = [];
        let s = 0, e = 10;
        while (s < user_ids.length) {
          split_uids.push(user_ids.slice(s, e));
          s = e;
          e += 10;
        }
        const remove_taggings = function () {
          split_uids.forEach(function (user_ids_chunk) {
            const uids_param = 'user_id=' + user_ids_chunk.join('&user_id=');
            $.ajax({
              type: 'DELETE',
              url: api_url + 'taggings/?tag_slug=' + tag_slug + '&' + uids_param,
            }).done(function () {
              user_ids_chunk.forEach(function (user_id) {
                $('[data-user-id="' + user_id + '"] ' +
                  '.colortag[data-tagslug="' + tag_slug +'"]'
                ).remove();
                // Remove tag from tag_slugs
                const tag_slugs = participants_
                  .find(function (p) { return p.user_id === user_id; })
                  .tag_slugs;
                const slug_index = tag_slugs.findIndex(function (t) {return t === tag_slug});
                if (slug_index > -1) {
                  tag_slugs.splice(slug_index, 1);
                }
              });
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
