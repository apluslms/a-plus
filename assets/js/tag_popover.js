function add_colortag_buttons(api_url, mutation_target, participants) {
  if (typeof get_users_for_user !== 'function') {
    get_users_for_user = function (user_id) {
      return function () { return [user_id]; };
    };
  }
  if (!api_url.endsWith('/')) {
    api_url = api_url + '/';
  }

  // Get popover button dictionaries
  const colortag_buttons = function (elem) {
    const $elem = $(elem);
    const tag_id_raw = $elem.attr('data-tagid');
    const tag_id = parseInt(tag_id_raw, 10);
    const tag_slug = $elem.attr('data-tagslug');
    const user_id = parseInt(
      $elem.parents('[data-user-id]').attr('data-user-id'), 10
    );
    const tag_key = isNaN(tag_id) || tag_id_raw === '' ? tag_slug : tag_id;
    const button_id_prefix = 'participant-' + user_id + '-tag-' + tag_key + '-';
    // Define a 'fake' participants list if it is not defined, to work
    // seamlessly on both the participants list page and other pages
    const participants_ = participants ? participants : [{
      user_id: user_id,
      tag_slugs: [tag_slug],
    }];

    const filter_button = {
      id: button_id_prefix + 'filter',
      classes: 'btn-outline-secondary btn-sm',
      text: _('Toggle filtering by tag'),
      onclick: function () {
        $('.filter-users button[data-tagslug="' + tag_slug + '"]').trigger('click');
        return false;
      },
    };
    const remove_button = {
      id: button_id_prefix + 'remove',
      classes: 'btn-danger btn-sm',
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
          let pendingChunks = split_uids.length;
          // Resolve numeric tag id (if any) from page filter buttons
          let removedTagId = null;
          try {
            const idAttr = $('.filter-users button.filter-tag[data-tagslug="' + tag_slug + '"]').attr('data-tagid');
            const parsed = parseInt(idAttr, 10);
            removedTagId = isNaN(parsed) ? null : parsed;
          } catch (e) { /* ignore */ }
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
                // Remove Id from tag_ids if present
                if (removedTagId !== null) {
                  const p = participants_.find(function (pp) { return pp.user_id === user_id; });
                  if (p && Array.isArray(p.tag_ids)) {
                    const idIdx = p.tag_ids.indexOf(removedTagId);
                    if (idIdx > -1) p.tag_ids.splice(idIdx, 1);
                  }
                }
              });
              // When all chunks have completed, announce change and refresh filters
              pendingChunks -= 1;
              if (pendingChunks === 0) {
                try {
                  $(document).trigger('aplus:tags-changed', { type: 'remove', tag_slug: tag_slug, user_ids: user_ids });
                } catch (e) { /* ignore */ }
                // Fallback: if DataTables is present, force a redraw
                try {
                  if ($.fn.dataTable && $('#table-participants').length) {
                    $('#table-participants').DataTable().draw(false);
                  }
                } catch (e) { /* ignore */ }
              }
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
  const is_hardcoded = function($elem) {
    const slug = $elem.attr('data-tagslug');
    const idRaw = $elem.attr('data-tagid');
    const idNum = parseInt(idRaw, 10);
    return slug === 'user-internal' || slug === 'user-external' || idRaw === '' || isNaN(idNum);
  };
  const get_title_for_elem = function($elem) {
    const slug = $elem.attr('data-tagslug');
    if (!slug) return '';
    const $btn = $('.filter-users button.filter-tag[data-tagslug="' + slug + '"]');
    // Prefer explicit description; fallback to name/text
    const desc = $btn.attr('data-description');
    if (desc && desc.trim()) return desc;
    const name = $btn.attr('data-tagname') || $btn.text().trim();
    return name || '';
  };

  const mutation_callback = function (mutationsList) {
    mutationsList.forEach(function (mutation) {
      const $added = $(mutation.addedNodes);
      $added.each(function (i, elem) {
        const $elem = $(elem);
        // Check both the node itself and any matching descendants
        const $targets = $elem.is(tag_selector)
          ? $elem
          : $elem.find(tag_selector);
        $targets.each(function(){
          const $t = $(this);
          if (is_hardcoded($t)) return;
          if ($t.data('aplusPopoverInit') === true) return;
          const title = get_title_for_elem($t);
          $t.buttons_popover(colortag_buttons, { title: title });
          $t.data('aplusPopoverInit', true);
        });
      });
    });
  };
  // Set up a single observer per mutation_target
  const mt = mutation_target;
  if (mt && !mt._aplusTagObserver) {
    mt._aplusTagObserver = new MutationObserver(mutation_callback);
    mt._aplusTagObserver.observe(mt, { childList: true, subtree: true });
  }

  $(tag_selector).filter(function(){ return !is_hardcoded($(this)); }).each(function(){
    const $e = $(this);
    if ($e.data('aplusPopoverInit') === true) return;
    const title = get_title_for_elem($e);
    $e.buttons_popover(colortag_buttons, { title: title });
    $e.data('aplusPopoverInit', true);
  });
}
