(function ($) {
  $(document).on('aplus:translation-ready', function() {
    const tag_dropdown_handles = {};
    $('.usertags-container').each(function() {
      const $container = $(this);
      const add_text = _("Add new tagging");
      const user_id = $container.data('user-id');
      const tag_ids = $container.find('.colortag').map(function() {
        return $(this).data('tagid');
      }).get();
      const get_users = (typeof get_users_for_user === 'function') ?
        get_users_for_user(user_id) :
        function() { return [user_id]; };
      const add_taggings_id = 'add-taggings-' + user_id;

      tag_dropdown_handles[user_id] = create_tagging_dropdown(
        tag_ids,
        get_users,
        add_text,
        add_taggings_id,
        function ($elem) {
          if ($elem.find('.colortag').length > 0)
            $container.prepend($elem);
        },
        function (jqXHRs, tags_xhr) { tags_xhr.done(function (data_tags) {
          const tags = data_tags.results; //FIXME course tags might be paginated and this only reads the first page
          jqXHRs.forEach(function (jqXHR) {
            jqXHR.done(function (data) {
              const tag = tags.find(function (tag) {
                return tag.id === data.tag.id; });
              // This callback may be called for multiple taggings (because
              // the same tag may be added to multiple students at once), hence
              // the tag must be added to the right container in the DOM.
              const $usertags = $('.usertags-container[data-user-id="' + data.user.id + '"] > .usertags-slots');
              $usertags.append(' ',django_colortag_badge(tag));
              if (typeof extra_click_handler === 'function') {
                 extra_click_handler(data);
              }
            });
          });
        });},
        'aplus-button--secondary aplus-button--xs'
      );
    });

    // When a tag is removed via the popover on a single-user page, re-add it
    // to the dropdown so it can be immediately re-applied if needed.
    // On multi-user pages (e.g. participants list) removal is handled
    // differently and the dropdowns are replaced by modals, so no handler
    // is needed there.
    if ($('.usertags-container').length === 1) {
      $(document).on('aplus:tags-changed', function (e, data) {
        if (data.type !== 'remove') return;
        data.user_ids.forEach(function (uid) {
          const handle = tag_dropdown_handles[uid];
          if (handle && typeof handle.readd_tag === 'function') {
            handle.readd_tag(data.tag_slug);
          }
        });
      });
    }
  });
})(jQuery);
